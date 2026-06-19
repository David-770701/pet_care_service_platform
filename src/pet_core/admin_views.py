from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q, Avg, Exists, OuterRef, Count
from django.db import transaction
import json
from datetime import timedelta
from django.core.paginator import Paginator
from django.utils.dateparse import parse_datetime

from .models import User, PetOwner, Merchant, Pet, Service, ServiceCategory, Order, Review, VaccineRecord, FavoriteStore, Vaccine, VaccineOrderDetail
from .vaccine_logic import (
    build_due_vaccine_reminders,
    calculate_next_due_date,
    get_pet_vaccine_queryset,
    normalize_species_name,
)
from .view_helpers import *
from .decorators import role_required

@role_required('admin')
def admin_dashboard(request):

    total_users = User.objects.count()
    owner_count = User.objects.filter(role='owner').count()
    merchant_count = User.objects.filter(role='merchant').count()
    admin_count = User.objects.filter(role='admin').count()

    pending_merchants = Merchant.objects.filter(is_verified=False, user__is_active=False).count()
    verified_merchants = Merchant.objects.filter(is_verified=True).count()

    total_orders = Order.objects.count()
    total_reviews = Review.objects.count()

    context = {
        'total_users': total_users,
        'owner_count': owner_count,
        'merchant_count': merchant_count,
        'admin_count': admin_count,
        'pending_merchants': pending_merchants,
        'verified_merchants': verified_merchants,
        'total_orders': total_orders,
        'total_reviews': total_reviews,
    }
    return render(request, 'pet_core/admin_dashboard.html', context)

@role_required('admin')
def admin_pending_merchants(request):

    return redirect('admin_merchant_list')

@role_required('admin')
def admin_approve_merchant(request, merchant_id):

    merchant = get_object_or_404(Merchant, user_id=merchant_id)
    if request.method == 'POST':
        if request.POST.get('confirmed') != '1':
            messages.info(request, 'Operation cancelled.')
            return redirect('admin_merchant_list')
        if not _merchant_is_pending_for_review(merchant):
            messages.error(request, 'This merchant is already reviewed and cannot be approved again.')
            return redirect('admin_merchant_list')
        merchant.is_verified = True
        merchant.save()
        merchant.user.is_active = True
        merchant.user.save()
        messages.success(request, f'Approved merchant: {merchant.store_name}.')
    return redirect('admin_merchant_list')

@role_required('admin')
def admin_reject_merchant(request, merchant_id):

    merchant = get_object_or_404(Merchant, user_id=merchant_id)
    if request.method == 'POST':
        if request.POST.get('confirmed') != '1':
            messages.info(request, 'Operation cancelled.')
            return redirect('admin_merchant_list')
        if not _merchant_is_pending_for_review(merchant):
            messages.error(request, 'This merchant is already reviewed and cannot return to pending.')
            return redirect('admin_merchant_list')
        username = merchant.user.username
        merchant.user.delete()
        messages.info(request, f'Rejected merchant registration: {username}.')
    return redirect('admin_merchant_list')

@role_required('admin')
def admin_user_list(request):

    status = request.GET.get('status', '')
    users = User.objects.filter(role='owner').order_by('-date_joined')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'disabled':
        users = users.filter(is_active=False)

    paginator = Paginator(users, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'pet_core/admin_users.html', {'page_obj': page_obj, 'status': status})

@role_required('admin')
def admin_toggle_user_active(request, user_id):

    target = get_object_or_404(User, id=user_id)
    if target.id == request.user.id:
        messages.error(request, 'You cannot disable your own account.')
        return redirect('admin_user_list')

    if target.role != 'owner':
        messages.error(request, 'This page only manages Pet Owner accounts.')
        return redirect('admin_user_list')

    if request.method == 'POST':
        if request.POST.get('confirmed') != '1':
            messages.info(request, 'Operation cancelled.')
            return redirect('admin_user_list')
        target.is_active = not target.is_active
        target.save()
        messages.success(request, f'Updated user {target.username} status.')
    return redirect('admin_user_list')

@role_required('admin')
def admin_merchant_list(request):

    status = (request.GET.get('status') or '').strip().lower()
    pending = (request.GET.get('pending_services') or '').strip().lower()

    merchants = Merchant.objects.select_related('user').annotate(services_count=Count('services'))

    if status in {'active', 'banned'}:
        merchants = merchants.filter(user__is_active=(status == 'active'))

    if pending in {'has', 'none'}:
        has_pending = Exists(
            Service.objects.filter(merchant_id=OuterRef('pk'), approval_status='pending')
        )
        merchants = merchants.annotate(has_pending_services=has_pending)
        merchants = merchants.filter(has_pending_services=(pending == 'has'))

    merchants = merchants.order_by('-average_rating', 'user_id')
    paginator = Paginator(merchants, 30)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(
        request,
        'pet_core/admin_merchants.html',
        {
            'page_obj': page_obj,
            'filter_status': status,
            'filter_pending_services': pending,
        },
    )

@role_required('admin')
def admin_merchant_services_fragment(request, merchant_id):

    merchant = get_object_or_404(Merchant.objects.select_related('user'), user_id=merchant_id)
    services = (
        Service.objects.filter(merchant_id=merchant.user_id)
        .select_related('category')
        .order_by('approval_status', 'id')
    )
    return render(
        request,
        'pet_core/admin_merchant_services_fragment.html',
        {
            'merchant': merchant,
            'services': services,
        },
    )

@role_required('admin')
def admin_delete_merchant(request, merchant_id):

    merchant = get_object_or_404(Merchant, user_id=merchant_id)
    if request.method == 'POST':
        if request.POST.get('confirmed') != '1':
            messages.info(request, 'Operation cancelled.')
            return redirect('admin_merchant_list')
        merchant.user.is_active = not merchant.user.is_active
        merchant.user.save(update_fields=['is_active'])
        messages.success(request, f'Updated merchant {merchant.user.username} status.')
    return redirect('admin_merchant_list')

@role_required('admin')
def admin_delete_service(request, service_id):

    if request.method != 'POST':
        return redirect('admin_merchant_list')

    service = get_object_or_404(Service, id=service_id)
    active_orders = service.orders.exclude(status__in=['completed', 'cancelled']).exists()
    if active_orders:
        messages.error(request, 'Cannot disable service. There are unfinished orders linked to it.')
        return redirect('admin_merchant_list')

    if request.POST.get('confirmed') != '1':
        messages.info(request, 'Operation cancelled.')
        return redirect('admin_merchant_list')

    service.is_admin_disabled = True
    service.save(update_fields=['is_admin_disabled'])
    messages.success(request, 'Service has been disabled by admin.')
    return redirect('admin_merchant_list')

@role_required('admin')
def admin_service_list(request):
    return redirect('admin_merchant_list')

@role_required('admin')
def admin_approve_service(request, service_id):
    if request.method != 'POST':
        return redirect('admin_merchant_list')
    service = get_object_or_404(Service, id=service_id)
    if request.POST.get('confirmed') != '1':
        messages.info(request, 'Operation cancelled.')
        return redirect('admin_merchant_list')
    service.approval_status = 'approved'
    service.is_admin_disabled = False
    service.save(update_fields=['approval_status', 'is_admin_disabled'])
    messages.success(request, 'Service approved and published.')
    return redirect('admin_merchant_list')

@role_required('admin')
def admin_review_list(request):

    username = (request.GET.get('username') or '').strip()
    reviews = Review.objects.select_related('order__service__merchant__user', 'order__owner__user')
    if username:
        raw = username
        if '*' in raw:
            core = raw.replace('*', '').strip()
            if core:
                if raw.startswith('*') and raw.endswith('*'):
                    reviews = reviews.filter(order__owner__user__username__icontains=core)
                elif raw.endswith('*'):
                    reviews = reviews.filter(order__owner__user__username__startswith=core)
                elif raw.startswith('*'):
                    reviews = reviews.filter(order__owner__user__username__endswith=core)
        else:
            reviews = reviews.filter(order__owner__user__username=username)

    reviews = reviews.order_by('-created_at')
    paginator = Paginator(reviews, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'pet_core/admin_reviews.html', {'page_obj': page_obj, 'username': username})

@role_required('admin')
def admin_delete_review(request, order_id):

    review = get_object_or_404(Review, order_id=order_id)
    if request.method == 'POST':
        if request.POST.get('confirmed') != '1':
            messages.info(request, 'Operation cancelled.')
            return redirect('admin_review_list')
        review.delete()
        messages.success(request, 'Review deleted and merchant rating updated.')
    return redirect('admin_review_list')
