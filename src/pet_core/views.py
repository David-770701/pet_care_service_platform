"""Compatibility exports for URL routing and older imports.

The actual view implementations are split by product area.
"""

from .auth_views import *
from .public_views import *
from .owner_views import *
from .merchant_views import *
from .admin_views import *

__all__ = ['home_view', 'login_view', 'register_view', 'logout_view', 'merchant_list', 'merchant_detail', 'service_list', 'book_service', 'cancel_order', 'owner_dashboard', 'vaccine_reminders', 'add_pet', 'edit_pet', 'delete_pet', 'pet_vaccines', 'toggle_favorite', 'favorite_list', 'pay_order', 'write_review', 'my_reviews', 'edit_profile', 'merchant_dashboard', 'edit_store_profile', 'add_service', 'edit_service', 'delete_service', 'update_order_status', 'merchant_reviews', 'admin_dashboard', 'admin_pending_merchants', 'admin_approve_merchant', 'admin_reject_merchant', 'admin_user_list', 'admin_toggle_user_active', 'admin_merchant_list', 'admin_merchant_services_fragment', 'admin_delete_merchant', 'admin_delete_service', 'admin_service_list', 'admin_approve_service', 'admin_review_list', 'admin_delete_review']
