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
from .forms import MerchantStoreForm, ServiceForm

@role_required('merchant')
def merchant_dashboard(request):
        
    merchant = request.user.merchant_profile
    services = merchant.services.all()
    orders = Order.objects.filter(service__merchant=merchant).order_by('-appointment_time')
    
    context = {
        'merchant': merchant,
        'services': services,
        'orders': orders,
    }
    return render(request, 'pet_core/merchant_dashboard.html', context)

@role_required('merchant')
def edit_store_profile(request):
    merchant = request.user.merchant_profile
    
    if request.method == 'POST':
        form = MerchantStoreForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, messages, form)
            return redirect('edit_store_profile')

        merchant.store_name = form.cleaned_data['store_name']
        merchant.province = form.cleaned_data['province']
        merchant.city = form.cleaned_data['city']
        merchant.district = form.cleaned_data['district']
        merchant.address_detail = form.cleaned_data['address_detail']
        merchant.contact_phone = form.cleaned_data['contact_phone']
        merchant.operating_hours = form.cleaned_data['operating_hours']
        merchant.description = form.cleaned_data['description']
        merchant.save()
        messages.success(request, 'Store profile updated successfully.')
        return redirect('merchant_dashboard')

    initial_province = merchant.province
    initial_city = merchant.city
    initial_district = merchant.district
    initial_detail = merchant.address_detail
    return render(
        request,
        'pet_core/edit_store.html',
        {
            'merchant': merchant,
            'initial_province': initial_province,
            'initial_city': initial_city,
            'initial_district': initial_district,
            'initial_address_detail': initial_detail,
        },
    )

@role_required('merchant')
def add_service(request):
    merchant = request.user.merchant_profile
    categories = ServiceCategory.objects.all()
    if merchant.primary_category_id:
        categories = categories.filter(id=merchant.primary_category_id)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, merchant=merchant)
        if not form.is_valid():
            flash_form_errors(request, messages, form)
            return redirect('add_service')

        category = form.cleaned_data['category']
        if not merchant.primary_category_id:
            merchant.primary_category = category
            merchant.save(update_fields=['primary_category'])

        service = form.save(commit=False)
        service.merchant = merchant
        service.category = category
        service.approval_status = 'pending'
        service.is_admin_disabled = False
        service.save()
        messages.success(request, 'New service added successfully.')
        return redirect('merchant_dashboard')
        
    show_vaccine_toggle = _is_medical_category(merchant.primary_category)
    return render(
        request,
        'pet_core/add_service.html',
        {'categories': categories, 'show_vaccine_toggle': show_vaccine_toggle},
    )

@role_required('merchant')
def edit_service(request, service_id):
    merchant = request.user.merchant_profile
    service = get_object_or_404(Service, id=service_id, merchant=merchant)
    categories = ServiceCategory.objects.all()
    if merchant.primary_category_id:
        categories = categories.filter(id=merchant.primary_category_id)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service, merchant=merchant)
        if not form.is_valid():
            flash_form_errors(request, messages, form)
            return redirect('edit_service', service_id=service.id)

        category = form.cleaned_data['category']
        if not merchant.primary_category_id:
            merchant.primary_category = category
            merchant.save(update_fields=['primary_category'])

        service = form.save(commit=False)
        service.category = category
        service.approval_status = 'pending'
        service.is_admin_disabled = False
        service.save(update_fields=[
            'name',
            'category',
            'description',
            'price',
            'approval_status',
            'is_admin_disabled',
            'is_vaccine_service',
        ])
        messages.success(request, 'Service updated and pending admin approval.')
        return redirect('merchant_dashboard')
        
    show_vaccine_toggle = _is_medical_category(service.category)
    return render(
        request,
        'pet_core/edit_service.html',
        {'service': service, 'categories': categories, 'show_vaccine_toggle': show_vaccine_toggle},
    )

@role_required('merchant')
def delete_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, merchant=request.user.merchant_profile)
    
    # Preserve order history by preventing deletion while active orders exist.
    unfinished_orders = service.orders.exclude(status__in=['completed', 'cancelled']).exists()
    if unfinished_orders:
        messages.error(request, 'Cannot delete this service. There are active orders linked to it.')
        return redirect('merchant_dashboard')

    if request.method != 'POST':
        return redirect('merchant_dashboard')

    if request.POST.get('confirmed') != '1':
        messages.info(request, 'Deletion aborted.')
        return redirect('merchant_dashboard')

    service.delete()
    messages.success(request, 'Service deleted successfully.')
    return redirect('merchant_dashboard')

@role_required('merchant')
def update_order_status(request, order_id):
        
    if request.method == 'POST':
        order = get_object_or_404(
            Order.objects.select_related('vaccine_detail__vaccine', 'service__merchant', 'pet'),
            id=order_id,
            service__merchant=request.user.merchant_profile,
        )
        new_status = request.POST.get('status')
        
        allowed_transitions = {
            'pending': {'confirmed', 'cancelled'},
            'confirmed': {'completed'},
            'completed': set(),
            'cancelled': set(),
        }

        if new_status not in dict(Order.STATUS_CHOICES):
            messages.error(request, 'Invalid status.')
            return redirect('merchant_dashboard')

        if new_status == order.status:
            return redirect('merchant_dashboard')

        if new_status not in allowed_transitions.get(order.status, set()):
            messages.error(request, 'Invalid status transition.')
            return redirect('merchant_dashboard')

        if new_status == 'completed' and not order.amount_confirmed:
            messages.error(request, 'Cannot complete order. Owner has not confirmed the order amount yet.')
            return redirect('merchant_dashboard')

        with transaction.atomic():
            order.status = new_status
            order.save(update_fields=['status'])

            vaccine_detail = getattr(order, 'vaccine_detail', None)
            if new_status == 'completed' and vaccine_detail and vaccine_detail.vaccine_id:
                vaccine = vaccine_detail.vaccine
                administered_date = order.appointment_time.date()
                next_due = calculate_next_due_date(vaccine, administered_date)
                VaccineRecord.objects.create(
                    pet=order.pet,
                    vaccine=vaccine,
                    vaccine_name=vaccine.full_name or vaccine.vaccine_name,
                    administered_date=administered_date,
                    next_due_date=next_due,
                    remarks=vaccine_detail.remarks or '',
                )

        messages.success(request, f'Order #{order.id} status updated to {order.get_status_display()}.')
            
    return redirect('merchant_dashboard')

@role_required('merchant')
def merchant_reviews(request):
    merchant = request.user.merchant_profile
    reviews = Review.objects.filter(order__service__merchant=merchant).order_by('-created_at')
    return render(request, 'pet_core/merchant_reviews.html', {'reviews': reviews})
