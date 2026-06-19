from django.urls import path
from . import views

urlpatterns = [
    # Auth & Home
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),


    # Platform Admin
    path('platform-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('platform-admin/merchants/pending/', views.admin_pending_merchants, name='admin_pending_merchants'),
    path('platform-admin/merchant/<int:merchant_id>/approve/', views.admin_approve_merchant, name='admin_approve_merchant'),
    path('platform-admin/merchant/<int:merchant_id>/reject/', views.admin_reject_merchant, name='admin_reject_merchant'),
    path('platform-admin/users/', views.admin_user_list, name='admin_user_list'),
    path('platform-admin/user/<int:user_id>/toggle_active/', views.admin_toggle_user_active, name='admin_toggle_user_active'),
    path('platform-admin/merchants/', views.admin_merchant_list, name='admin_merchant_list'),
    path('platform-admin/merchant/<int:merchant_id>/delete/', views.admin_delete_merchant, name='admin_delete_merchant'),
    path('platform-admin/merchant/<int:merchant_id>/services-fragment/', views.admin_merchant_services_fragment, name='admin_merchant_services_fragment'),
    path('platform-admin/service/<int:service_id>/delete/', views.admin_delete_service, name='admin_delete_service'),
    path('platform-admin/service/<int:service_id>/approve/', views.admin_approve_service, name='admin_approve_service'),
    path('platform-admin/reviews/', views.admin_review_list, name='admin_review_list'),
    path('platform-admin/review/<int:order_id>/delete/', views.admin_delete_review, name='admin_delete_review'),
    
    # Public
    path('merchants/', views.merchant_list, name='merchant_list'),
    path('merchant/<int:merchant_id>/', views.merchant_detail, name='merchant_detail'),
    
    # Pet Owner
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/profile/edit/', views.edit_profile, name='edit_profile'),
    path('owner/add_pet/', views.add_pet, name='add_pet'),
    path('owner/pet/<int:pet_id>/edit/', views.edit_pet, name='edit_pet'),
    path('owner/pet/<int:pet_id>/delete/', views.delete_pet, name='delete_pet'),
    path('owner/pet/<int:pet_id>/vaccines/', views.pet_vaccines, name='pet_vaccines'),
    path('owner/reminders/', views.vaccine_reminders, name='vaccine_reminders'),
    path('owner/favorites/', views.favorite_list, name='favorite_list'),
    path('owner/merchant/<int:merchant_id>/toggle_favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('owner/order/<int:order_id>/pay/', views.pay_order, name='pay_order'),
    path('owner/order/<int:order_id>/review/', views.write_review, name='write_review'),
    path('owner/order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('owner/reviews/', views.my_reviews, name='my_reviews'),
    
    # Public Services
    path('services/', views.service_list, name='service_list'),
    path('service/<int:service_id>/book/', views.book_service, name='book_service'),

    # Merchant
    path('merchant/dashboard/', views.merchant_dashboard, name='merchant_dashboard'),
    path('merchant/store/edit/', views.edit_store_profile, name='edit_store_profile'),
    path('merchant/service/add/', views.add_service, name='add_service'),
    path('merchant/service/<int:service_id>/edit/', views.edit_service, name='edit_service'),
    path('merchant/service/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    path('merchant/order/<int:order_id>/update/', views.update_order_status, name='update_order_status'),
    path('merchant/reviews/', views.merchant_reviews, name='merchant_reviews'),
]
