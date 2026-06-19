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

def home_view(request):
    return render(request, 'pet_core/home.html')

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        candidate = User.objects.filter(username=u).first()
        if candidate is not None:
            if candidate.role != 'merchant' and not candidate.is_active:
                messages.error(request, 'Your account has been disabled.')
                return redirect('login')
            if candidate.role == 'merchant' and not candidate.is_active:
                try:
                    merchant = candidate.merchant_profile
                    if not merchant.is_verified:
                        messages.error(request, 'Your merchant account is pending admin approval.')
                        return redirect('login')
                    messages.error(request, 'Your merchant account has been disabled.')
                    return redirect('login')
                except Merchant.DoesNotExist:
                    messages.error(request, 'Merchant profile not found.')
                    return redirect('login')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            if user.role == 'merchant':
                try:
                    merchant = user.merchant_profile
                    if not merchant.is_verified or not user.is_active:
                        if not merchant.is_verified:
                            messages.error(request, 'Your merchant account is pending admin approval.')
                        else:
                            messages.error(request, 'Your merchant account has been disabled.')
                        return redirect('login')
                except Merchant.DoesNotExist:
                    messages.error(request, 'Merchant profile not found.')
                    return redirect('login')
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            if user.role == 'owner':
                owner = user.pet_owner_profile
                due_soon = build_due_vaccine_reminders(owner)[:10]
                if due_soon:
                    request.session['vaccine_popup'] = [
                        {
                            'pet_name': item['pet'].name,
                            'vaccine_name': f"{item['series_name']} - {item['next_vaccine_name']}",
                            'next_due_date': item['record'].next_due_date.strftime('%Y-%m-%d'),
                        }
                        for item in due_soon
                    ]
                return redirect('owner_dashboard')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'pet_core/login.html')

def register_view(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        u = request.POST.get('username')
        e = request.POST.get('email')
        p = request.POST.get('password')

        province = request.POST.get('province', '')
        city = request.POST.get('city', '')
        district = request.POST.get('district', '')
        address_detail = request.POST.get('address_detail', '')
        if province in MUNICIPALITIES and not city:
            city = province

        if User.objects.filter(username=u).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')

        user = User.objects.create_user(username=u, email=e, password=p, role=role)

        if role == 'owner':
            phone = request.POST.get('phone', '')
            if province in MUNICIPALITIES and not city:
                city = province
            if (province or city or district or address_detail) and (not province or not city or not district):
                user.delete()
                messages.error(request, 'Please select province, city and district.')
                return redirect('register')
            PetOwner.objects.create(
                user=user,
                phone=phone,
                province=province,
                city=city,
                district=district,
                address_detail=address_detail,
            )
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('owner_dashboard')
        elif role == 'merchant':
            user.is_active = False # Merchant needs admin approval
            user.save()
            store_name = request.POST.get('store_name', '')
            license_number = request.POST.get('license_number', '')
            if province in MUNICIPALITIES and not city:
                city = province
            if not province or not city or not district:
                user.delete()
                messages.error(request, 'Please select province, city and district for store address.')
                return redirect('register')
            if not address_detail.strip():
                user.delete()
                messages.error(request, 'Please enter detailed store address.')
                return redirect('register')
            Merchant.objects.create(
                user=user,
                store_name=store_name,
                license_number=license_number,
                province=province,
                city=city,
                district=district,
                address_detail=address_detail,
            )
            messages.success(request, 'Registration successful! Your merchant account is pending admin approval.')
            return redirect('login')
        
    return render(request, 'pet_core/register.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')
