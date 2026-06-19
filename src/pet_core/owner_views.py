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
from .forms import OwnerProfileForm, PetEditForm, PetForm, ReviewForm

@role_required('owner')
def cancel_order(request, order_id):
    if request.method != 'POST':
        return redirect('owner_dashboard')

    if request.POST.get('confirmed') != '1':
        messages.info(request, 'Cancellation aborted.')
        return redirect('owner_dashboard')

    order = get_object_or_404(Order, id=order_id, owner=request.user.pet_owner_profile)
    if order.status != 'pending':
        messages.error(request, 'This order can no longer be cancelled.')
        return redirect('owner_dashboard')

    order.status = 'cancelled'
    order.save()
    messages.success(request, f'Order #{order.id} has been cancelled.')
    return redirect('owner_dashboard')

@role_required('owner')
def owner_dashboard(request):
    
    owner = request.user.pet_owner_profile
    pets = owner.pets.all()
    pet_species_map_json = json.dumps(
        {str(p.id): normalize_species_name(p.species) for p in pets},
        ensure_ascii=False,
    )
    orders = owner.orders.select_related('service__merchant__user', 'pet').order_by('-appointment_time')

    reviewed_order_ids = set(Review.objects.filter(order__in=orders).values_list('order_id', flat=True))
    for o in orders:
        o.has_review = o.id in reviewed_order_ids
    
    upcoming_vaccines = build_due_vaccine_reminders(owner)
    
    context = {
        'pets': pets,
        'orders': orders,
        'upcoming_vaccines': upcoming_vaccines,
        'vaccine_popup': request.session.pop('vaccine_popup', None),
    }
    return render(request, 'pet_core/owner_dashboard.html', context)

@role_required('owner')
def vaccine_reminders(request):
    owner = request.user.pet_owner_profile
    reminder_items = build_due_vaccine_reminders(owner)
    return render(request, 'pet_core/vaccine_reminders.html', {'reminder_items': reminder_items})

@role_required('owner')
def add_pet(request):
    species_choices = list(Pet.SPECIES_CHOICES)
        
    if request.method == 'POST':
        form = PetForm(request.POST)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.owner = request.user.pet_owner_profile
            pet.save()
            messages.success(request, f'Successfully added {pet.name} to your profile!')
            return redirect('owner_dashboard')
        flash_form_errors(request, messages, form)
        
    return render(request, 'pet_core/add_pet.html', {'species_choices': species_choices})

@role_required('owner')
def edit_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user.pet_owner_profile)
    if request.method == 'POST':
        form = PetEditForm(request.POST, instance=pet)
        if form.is_valid():
            pet = form.save()
            messages.success(request, f'{pet.name}\'s profile updated!')
            return redirect('owner_dashboard')
        flash_form_errors(request, messages, form)
    return render(request, 'pet_core/edit_pet.html', {'pet': pet})

@role_required('owner')
def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user.pet_owner_profile)
    # Check if there are unfinished orders
    unfinished_orders = pet.orders.exclude(status__in=['completed', 'cancelled']).exists()
    if unfinished_orders:
        messages.error(request, f'Cannot delete {pet.name} because there are unfinished orders.')
        return redirect('owner_dashboard')

    if request.method != 'POST':
        return redirect('owner_dashboard')

    if request.POST.get('confirmed') != '1':
        messages.info(request, 'Deletion aborted.')
        return redirect('owner_dashboard')

    pet.delete()
    messages.success(request, 'Pet deleted successfully.')
    return redirect('owner_dashboard')

@role_required('owner')
def pet_vaccines(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user.pet_owner_profile)
    vaccines = pet.vaccines.select_related('vaccine').all().order_by('-administered_date', '-id')
    vaccine_options = get_pet_vaccine_queryset(Vaccine, pet)
    
    if request.method == 'POST':
        vaccine_id = (request.POST.get('vaccine_id') or '').strip()
        a_date_raw = request.POST.get('administered_date')
        remarks = request.POST.get('remarks') or ''

        if not vaccine_id:
            messages.error(request, 'Please select a vaccine type.')
            return redirect('pet_vaccines', pet_id=pet.id)

        vaccine = get_object_or_404(Vaccine, v_id=vaccine_id)
        if normalize_species_name(vaccine.animal_type) != normalize_species_name(pet.species):
            messages.error(request, 'Selected vaccine type does not match your pet species.')
            return redirect('pet_vaccines', pet_id=pet.id)

        try:
            administered_date = timezone.datetime.fromisoformat(a_date_raw).date()
        except Exception:
            messages.error(request, 'Invalid administered date.')
            return redirect('pet_vaccines', pet_id=pet.id)

        next_due = calculate_next_due_date(vaccine, administered_date)

        VaccineRecord.objects.create(
            pet=pet,
            vaccine=vaccine,
            vaccine_name=vaccine.full_name or vaccine.vaccine_name,
            administered_date=administered_date,
            next_due_date=next_due,
            remarks=remarks,
        )
        messages.success(request, 'Vaccine record added successfully!')
        return redirect('pet_vaccines', pet_id=pet.id)
        
    return render(
        request,
        'pet_core/pet_vaccines.html',
        {'pet': pet, 'vaccines': vaccines, 'vaccine_options': vaccine_options},
    )

@role_required('owner')
def toggle_favorite(request, merchant_id):

    fallback = reverse('favorite_list')
    next_url = _safe_next_url(request, fallback)

    if request.method != 'POST':
        return redirect(next_url)
        
    merchant = get_object_or_404(Merchant, user_id=merchant_id)
    owner = request.user.pet_owner_profile
    
    if request.POST.get('confirmed') != '1':
        messages.info(request, 'Operation cancelled.')
        return redirect(next_url)

    fav, created = FavoriteStore.objects.get_or_create(owner=owner, merchant=merchant)
    if not created:
        fav.delete()
        messages.info(request, f'Removed {merchant.store_name} from your favorites.')
    else:
        messages.success(request, f'Added {merchant.store_name} to your favorites!')
        
    return redirect(next_url)

@role_required('owner')
def favorite_list(request):
    favorites = FavoriteStore.objects.filter(owner=request.user.pet_owner_profile).select_related('merchant')
    return render(request, 'pet_core/favorite_list.html', {'favorites': favorites})

@role_required('owner')
def pay_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, owner=request.user.pet_owner_profile, status='confirmed')
    if request.method == 'POST':
        if order.amount_confirmed:
            messages.info(request, 'Order amount is already confirmed.')
            return redirect('owner_dashboard')
        order.amount_confirmed = True
        order.save(update_fields=['amount_confirmed'])
        messages.success(request, 'Order amount confirmed. Please wait for the merchant to complete the service.')
        return redirect('owner_dashboard')
    return render(request, 'pet_core/pay_order.html', {'order': order})

@role_required('owner')
def write_review(request, order_id):
    order = get_object_or_404(Order, id=order_id, owner=request.user.pet_owner_profile, status='completed')
    if hasattr(order, 'review'):
        messages.warning(request, 'You have already reviewed this order.')
        return redirect('owner_dashboard')
        
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.create(
                order=order,
                rating=form.cleaned_data['rating'],
                comment=form.cleaned_data['comment'],
            )
            messages.success(request, 'Thank you for your review!')
            return redirect('owner_dashboard')
        flash_form_errors(request, messages, form)
        
    return render(request, 'pet_core/write_review.html', {'order': order})

@role_required('owner')
def my_reviews(request):
    reviews = Review.objects.filter(order__owner=request.user.pet_owner_profile).order_by('-created_at')
    return render(request, 'pet_core/my_reviews.html', {'reviews': reviews})

@role_required('owner')
def edit_profile(request):
    
    owner = request.user.pet_owner_profile
    if request.method == 'POST':
        form = OwnerProfileForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, messages, form)
            return redirect('edit_profile')

        request.user.email = form.cleaned_data['email']
        request.user.save()
        owner.phone = form.cleaned_data['phone']
        owner.province = form.cleaned_data['province']
        owner.city = form.cleaned_data['city']
        owner.district = form.cleaned_data['district']
        owner.address_detail = form.cleaned_data['address_detail']
        owner.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('owner_dashboard')

    initial_province = owner.province
    initial_city = owner.city
    initial_district = owner.district
    initial_detail = owner.address_detail
    return render(
        request,
        'pet_core/edit_profile.html',
        {
            'owner': owner,
            'initial_province': initial_province,
            'initial_city': initial_city,
            'initial_district': initial_district,
            'initial_address_detail': initial_detail,
        },
    )
