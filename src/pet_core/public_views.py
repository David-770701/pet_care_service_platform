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

def merchant_list(request):
    query = (request.GET.get('q') or '').strip()
    selected_cat = (request.GET.get('category') or '').strip()
    province_raw = request.GET.get('province')
    city_raw = request.GET.get('city')
    province = (province_raw or '').strip()
    city = (city_raw or '').strip()

    merchants = Merchant.objects.filter(is_verified=True)

    selected_category_obj = None
    if selected_cat and selected_cat.isdigit():
        selected_category_obj = ServiceCategory.objects.filter(id=int(selected_cat)).first()
        if selected_category_obj:
            merchants = merchants.filter(primary_category=selected_category_obj)

    if query:
        merchants = merchants.filter(store_name__icontains=query)

    apply_location_filter = bool(province or city)
    if apply_location_filter:
        if province:
            if province in MUNICIPALITIES and (not city or city == province):
                merchants = merchants.filter(province=province)
            elif city:
                merchants = merchants.filter(province=province, city=city)
            else:
                merchants = merchants.filter(province=province)
        else:
            merchants = merchants.filter(city=city)

    demo_licenses = {'LIC-BJ-001', 'LIC-SH-001'}
    pinned_merchants = []
    pinned_merchant_ids = []
    page_number = (request.GET.get('page') or '1').strip()
    if page_number in {'', '1'}:
        pinned_merchants = list(merchants.filter(license_number__in=demo_licenses).order_by('license_number'))
        pinned_merchant_ids = [m.user_id for m in pinned_merchants]

    merchants = merchants.order_by('-average_rating', 'user_id')
    paginator = Paginator(merchants, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'pet_core/merchant_list.html',
        {
            'page_obj': page_obj,
            'pinned_merchants': pinned_merchants,
            'pinned_merchant_ids': pinned_merchant_ids,
            'query': query,
            'selected_cat': selected_cat,
            'selected_category': selected_category_obj,
            'province': province,
            'city': city,
            'enforce_location': apply_location_filter,
        },
    )

def merchant_detail(request, merchant_id):
    merchant = get_object_or_404(Merchant, user_id=merchant_id)
    if not merchant.is_verified:
        allowed = False
        if request.user.is_authenticated:
            if request.user.role == 'admin':
                allowed = True
            elif request.user.role == 'merchant':
                try:
                    allowed = request.user.merchant_profile.user_id == merchant_id
                except Merchant.DoesNotExist:
                    allowed = False
            elif request.user.role == 'owner':
                try:
                    allowed = Order.objects.filter(owner=request.user.pet_owner_profile, service__merchant=merchant).exists()
                except PetOwner.DoesNotExist:
                    allowed = False

        if not allowed:
            return redirect('merchant_list')
    services = merchant.services.filter(is_active=True, approval_status='approved', is_admin_disabled=False).all()
    # Get reviews through the orders that belong to this merchant's services
    reviews_qs = Review.objects.filter(order__service__merchant=merchant).select_related('order__owner__user', 'order__service').order_by('-created_at')
    reviews_paginator = Paginator(reviews_qs, 10)
    reviews_page = reviews_paginator.get_page(request.GET.get('page'))
    
    is_favorited = False
    if request.user.is_authenticated and request.user.role == 'owner':
        is_favorited = merchant.favorited_by.filter(owner=request.user.pet_owner_profile).exists()
        
    context = {
        'merchant': merchant,
        'services': services,
        'reviews_page': reviews_page,
        'is_favorited': is_favorited,
    }
    return render(request, 'pet_core/merchant_detail.html', context)

def service_list(request):
    q = (request.GET.get('q') or '').strip()
    selected_cat = (request.GET.get('category') or '').strip()
    province_raw = request.GET.get('province')
    city_raw = request.GET.get('city')
    province = (province_raw or '').strip()
    city = (city_raw or '').strip()

    services = Service.objects.select_related('merchant', 'category').filter(
        is_active=True,
        approval_status='approved',
        is_admin_disabled=False,
        merchant__is_verified=True,
    )

    selected_category_obj = None
    if selected_cat and selected_cat.isdigit():
        selected_category_obj = ServiceCategory.objects.filter(id=int(selected_cat)).first()
        if selected_category_obj:
            services = services.filter(category=selected_category_obj)

    if q:
        services = services.filter(Q(name__icontains=q) | Q(merchant__store_name__icontains=q))
    else:
        if not selected_category_obj:
            services = services.none()
        else:
            apply_location_filter = bool(province or city)
            if apply_location_filter:
                if province:
                    if province in MUNICIPALITIES and (not city or city == province):
                        services = services.filter(merchant__province=province)
                    elif city:
                        services = services.filter(merchant__province=province, merchant__city=city)
                    else:
                        services = services.filter(merchant__province=province)
                else:
                    services = services.filter(merchant__city=city)

    demo_licenses = {'LIC-BJ-001', 'LIC-SH-001'}
    pinned_services = []
    pinned_service_ids = []
    page_number = (request.GET.get('page') or '1').strip()
    if page_number in {'', '1'} and selected_category_obj:
        pinned_services = list(
            services.filter(merchant__license_number__in=demo_licenses).order_by('-id')
        )
        pinned_service_ids = [s.id for s in pinned_services]

    services = services.order_by('-id')
    paginator = Paginator(services, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'pet_core/service_list.html',
        {
            'page_obj': page_obj,
            'pinned_services': pinned_services,
            'pinned_service_ids': pinned_service_ids,
            'query': q,
            'selected_cat': selected_cat,
            'selected_category': selected_category_obj,
            'province': province,
            'city': city,
            'enforce_location': bool(province or city),
        },
    )

@role_required('owner')
def book_service(request, service_id):
    if request.user.role != 'owner':
        messages.error(request, 'Only Pet Owners can book services.')
        return redirect('service_list')

    service = get_object_or_404(Service.objects.select_related('merchant', 'category'), id=service_id)
    if not service.is_active or service.approval_status != 'approved' or service.is_admin_disabled:
        messages.error(request, 'This service is currently unavailable for booking.')
        return redirect('service_list')
    if not service.merchant.is_verified:
        messages.error(request, 'This merchant is not verified yet. Booking is not available.')
        return redirect('service_list')

    hours = _parse_operating_hours(service.merchant.operating_hours)
    if hours is None:
        messages.error(request, 'This merchant has invalid operating hours configuration.')
        return redirect('service_list')
    start_t, end_t = hours
    owner = request.user.pet_owner_profile
    pets = owner.pets.all()
    pet_species_map_json = json.dumps(
        {str(p.id): normalize_species_name(p.species) for p in pets},
        ensure_ascii=False,
    )

    is_vaccine_booking = bool(service.is_vaccine_service and _is_medical_service(service))
    vaccines_by_type = {}
    if is_vaccine_booking:
        for v in Vaccine.objects.all().order_by('animal_type', 'vaccine_name', 'dose_number'):
            vaccines_by_type.setdefault(v.animal_type, []).append(
                {
                    'id': v.v_id,
                    'name': v.vaccine_name,
                    'full_name': v.full_name or v.vaccine_name,
                    'dose_number': v.dose_number,
                    'is_booster': v.is_booster,
                }
            )
    vaccines_by_type_json = json.dumps(vaccines_by_type, ensure_ascii=False)
    
    if not pets.exists():
        messages.warning(request, 'You need to add a pet before booking a service.')
        return redirect('add_pet')
        
    if request.method == 'POST':
        pet_id = request.POST.get('pet_id')
        appt_time = request.POST.get('appointment_time')
        vaccine_id = (request.POST.get('vaccine_id') or '').strip()
        vaccine_remarks = request.POST.get('vaccine_remarks') or ''

        appt_dt = parse_datetime(appt_time)
        if appt_dt is None:
            messages.error(request, 'Invalid appointment time format.')
            return redirect('book_service', service_id=service.id)
        if timezone.is_naive(appt_dt):
            appt_dt = timezone.make_aware(appt_dt, timezone.get_current_timezone())

        now = timezone.now()
        if appt_dt <= now:
            messages.error(request, 'Appointment time cannot be earlier than the current time.')
            return redirect('book_service', service_id=service.id)

        appt_t = appt_dt.astimezone(timezone.get_current_timezone()).time()
        if not (start_t <= appt_t <= end_t):
            messages.error(request, 'Booking failed: appointment time is outside merchant operating hours.')
            return redirect('book_service', service_id=service.id)
        
        pet = get_object_or_404(Pet, id=pet_id, owner=owner)

        selected_vaccine = None
        if is_vaccine_booking:
            pet_animal_type = normalize_species_name(pet.species)
            if not Vaccine.objects.filter(animal_type=pet_animal_type).exists():
                messages.error(request, 'No vaccines are available for this pet type in the current dataset.')
                return redirect('book_service', service_id=service.id)
            if not vaccine_id:
                messages.error(request, 'Please select a vaccine type.')
                return redirect('book_service', service_id=service.id)
            selected_vaccine = get_object_or_404(Vaccine, v_id=vaccine_id)
            if normalize_species_name(selected_vaccine.animal_type) != normalize_species_name(pet.species):
                messages.error(request, 'Selected vaccine type does not match your pet species.')
                return redirect('book_service', service_id=service.id)

        if (
            Order.objects.filter(pet=pet, appointment_time=appt_dt)
            .exclude(status='cancelled')
            .exists()
        ):
            messages.error(request, 'This pet already has an appointment at the selected time.')
            return redirect('book_service', service_id=service.id)
        
        order = Order.objects.create(
            owner=owner,
            service=service,
            pet=pet,
            appointment_time=appt_dt,
            status='pending',
        )
        if is_vaccine_booking:
            VaccineOrderDetail.objects.create(
                order=order,
                vaccine=selected_vaccine,
                remarks=vaccine_remarks,
            )
        messages.success(request, f'Successfully booked {service.name} for {pet.name}!')
        return redirect('owner_dashboard')
        
    return render(
        request,
        'pet_core/book_service.html',
        {
            'service': service,
            'pets': pets,
            'is_vaccine_booking': is_vaccine_booking,
            'vaccines_by_type_json': vaccines_by_type_json,
            'pet_species_map_json': pet_species_map_json,
        },
    )
