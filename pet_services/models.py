from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('owner', 'Pet Owner'),
        ('merchant', 'Merchant'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    phone = models.CharField(max_length=20, blank=True)
    groups = models.ManyToManyField(
        Group,
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='user_set',
        related_query_name='user',
        verbose_name='groups',
        db_table='django_user_groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='user_set',
        related_query_name='user',
        verbose_name='user permissions',
        db_table='django_user_user_permissions',
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class PetOwner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='pet_owner_profile')
    phone = models.CharField(max_length=20, blank=True)
    province = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=50, blank=True)
    district = models.CharField(max_length=50, blank=True)
    address_detail = models.TextField(blank=True)

    def __str__(self):
        return f"Owner: {self.user.username}"


class Administrator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='admin_profile')
    phone = models.CharField(max_length=20, blank=True)
    employee_no = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Admin: {self.user.username}"

class Merchant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='merchant_profile')
    primary_category = models.ForeignKey('ServiceCategory', on_delete=models.SET_NULL, null=True, blank=True, related_name='merchants')
    store_name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=100, unique=True)
    province = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=50, blank=True)
    district = models.CharField(max_length=50, blank=True)
    address_detail = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    operating_hours = models.CharField(max_length=50, default="9:00-18:00")
    description = models.TextField(blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    is_verified = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['province', 'city'], name='idx_merchant_province_city'),
            models.Index(fields=['is_verified', 'primary_category'], name='idx_merchant_verified_cat'),
        ]

    def __str__(self):
        return self.store_name

class Pet(models.Model):
    SPECIES_CHOICES = (
        ('Bird', 'Bird'),
        ('Cat', 'Cat'),
        ('Dog', 'Dog'),
        ('Ferret', 'Ferret'),
        ('Hamster', 'Hamster'),
        ('Hedgehog', 'Hedgehog'),
        ('Rabbit', 'Rabbit'),
        ('Snake', 'Snake'),
        ('Turtle', 'Turtle'),
    )
    owner = models.ForeignKey(PetOwner, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50, choices=SPECIES_CHOICES)
    breed = models.CharField(max_length=50, blank=True)
    age = models.IntegerField()
    weight = models.FloatField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=(('M', 'Male'), ('F', 'Female')))

    def __str__(self):
        return f"{self.name} ({self.species})"

class ServiceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True) # e.g., Boarding, Grooming, Medical

    def __str__(self):
        return self.name

class Service(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, related_name='services')
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    APPROVAL_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
    )
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='pending')
    is_admin_disabled = models.BooleanField(default=False)
    is_vaccine_service = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['merchant', 'name'], name='uniq_service_name_per_merchant'),
        ]
        indexes = [
            models.Index(fields=['category', 'merchant'], name='idx_service_category_merchant'),
            models.Index(fields=['merchant', 'is_active', 'approval_status', 'is_admin_disabled'], name='idx_service_merch_state'),
            models.Index(fields=['category', 'is_active', 'approval_status', 'is_admin_disabled', 'id'], name='idx_service_cat_state_id'),
            models.Index(fields=['category', 'is_active', 'approval_status', 'is_admin_disabled', 'merchant', 'id'], name='idx_srv_cat_state_merch_id'),
        ]

    def __str__(self):
        return f"{self.name} - {self.merchant.store_name}"

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', '待确认'),
        ('confirmed', '已确认（待付款）'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )
    owner = models.ForeignKey(PetOwner, on_delete=models.CASCADE, related_name='orders')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='orders')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='orders')
    appointment_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['service']),
            models.Index(fields=['status']),
            models.Index(fields=['appointment_time']),
            models.Index(fields=['pet', 'appointment_time'], name='idx_order_pet_time'),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.status}"


class VaccineOrderDetail(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, primary_key=True, related_name='vaccine_detail')
    vaccine = models.ForeignKey('Vaccine', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_details')
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Vaccine detail for Order #{self.order_id}"

class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for Order #{self.order_id} - {self.rating} Stars"

class VaccineRecord(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='vaccines')
    vaccine = models.ForeignKey('Vaccine', on_delete=models.SET_NULL, null=True, blank=True, related_name='records')
    vaccine_name = models.CharField(max_length=100)
    administered_date = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['pet', 'administered_date'], name='idx_vacrec_pet_admin'),
            models.Index(fields=['pet', 'next_due_date'], name='idx_vacrec_pet_due'),
        ]

    def __str__(self):
        return f"{self.vaccine_name} for {self.pet.name}"


class Vaccine(models.Model):
    v_id = models.CharField(max_length=10, primary_key=True)
    series_id = models.CharField(max_length=10, db_index=True)
    vaccine_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=150, blank=True)
    dose_number = models.PositiveIntegerField(default=1)
    is_booster = models.BooleanField(default=False)
    total_basic_doses = models.PositiveIntegerField(default=1)
    animal_type = models.CharField(max_length=50)

    class Meta:
        indexes = [
            models.Index(fields=['animal_type']),
            models.Index(fields=['series_id', 'dose_number']),
        ]

    def __str__(self):
        return f"{self.vaccine_name} ({self.animal_type})"

class FavoriteStore(models.Model):
    owner = models.ForeignKey(PetOwner, on_delete=models.CASCADE, related_name='favorites')
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'merchant')

    def __str__(self):
        return f"{self.owner.user.username} favorites {self.merchant.store_name}"
