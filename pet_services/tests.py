from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ServiceForm
from .models import Merchant, Order, Pet, PetOwner, Review, Service, ServiceCategory, User
from .vaccine_logic import calculate_next_due_date


class PetCoreTestDataMixin:
    def setUp(self):
        self.owner_user = User.objects.create_user(
            username='owner',
            password='pass12345',
            role='owner',
        )
        self.owner = PetOwner.objects.create(user=self.owner_user, phone='10086')
        self.pet = Pet.objects.create(
            owner=self.owner,
            name='Milo',
            species='Cat',
            breed='Domestic',
            age=2,
            weight=4.5,
            gender='M',
        )
        self.merchant_user = User.objects.create_user(
            username='merchant',
            password='pass12345',
            role='merchant',
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            store_name='Healthy Paws',
            license_number='LIC-TEST-001',
            province='Shanghai',
            city='Shanghai',
            district='Pudong',
            address_detail='No. 1 Test Road',
            is_verified=True,
        )
        self.category = ServiceCategory.objects.create(name='Pet Medical')
        self.service = Service.objects.create(
            merchant=self.merchant,
            category=self.category,
            name='Basic Checkup',
            description='Routine health check.',
            price=Decimal('99.00'),
            approval_status='approved',
        )


class ServiceFormTests(PetCoreTestDataMixin, TestCase):
    def test_service_name_must_be_unique_per_merchant(self):
        form = ServiceForm(
            data={
                'name': self.service.name,
                'category': self.category.id,
                'description': 'Duplicate service.',
                'price': '88.00',
            },
            merchant=self.merchant,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class ReviewRatingTests(PetCoreTestDataMixin, TestCase):
    def test_review_create_and_delete_recalculate_merchant_rating(self):
        order_one = self._create_completed_order()
        order_two = self._create_completed_order()

        review_one = Review.objects.create(order=order_one, rating=5)
        Review.objects.create(order=order_two, rating=3)
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.average_rating, Decimal('4.00'))

        review_one.delete()
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.average_rating, Decimal('3.00'))

    def _create_completed_order(self):
        return Order.objects.create(
            owner=self.owner,
            service=self.service,
            pet=self.pet,
            appointment_time=timezone.now(),
            status='completed',
            amount_confirmed=True,
        )


class MerchantOrderFlowTests(PetCoreTestDataMixin, TestCase):
    def test_merchant_cannot_complete_order_before_owner_confirms_amount(self):
        order = Order.objects.create(
            owner=self.owner,
            service=self.service,
            pet=self.pet,
            appointment_time=timezone.now(),
            status='confirmed',
            amount_confirmed=False,
        )
        self.client.login(username='merchant', password='pass12345')

        self.client.post(reverse('update_order_status', args=[order.id]), {'status': 'completed'})

        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')


class VaccineLogicTests(SimpleTestCase):
    def test_basic_series_next_dose_is_due_in_21_days(self):
        vaccine = SimpleNamespace(is_booster=False, dose_number=1, total_basic_doses=3)
        administered = timezone.datetime(2026, 6, 1).date()

        self.assertEqual(calculate_next_due_date(vaccine, administered), timezone.datetime(2026, 6, 22).date())

    def test_booster_is_due_in_one_year(self):
        vaccine = SimpleNamespace(is_booster=True, dose_number=3, total_basic_doses=3)
        administered = timezone.datetime(2026, 6, 1).date()

        self.assertEqual(calculate_next_due_date(vaccine, administered), timezone.datetime(2027, 6, 1).date())
