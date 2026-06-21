from django import forms

from .models import Pet, Service, ServiceCategory
from .view_helpers import MUNICIPALITIES, _is_medical_category


class AddressValidationMixin:
    address_required = False

    def clean(self):
        cleaned = super().clean()
        province = (cleaned.get('province') or '').strip()
        city = (cleaned.get('city') or '').strip()
        district = (cleaned.get('district') or '').strip()
        address_detail = (cleaned.get('address_detail') or '').strip()

        if province in MUNICIPALITIES and not city:
            cleaned['city'] = province
            city = province

        has_any_address = any([province, city, district, address_detail])
        if self.address_required or has_any_address:
            if not province or not city or not district:
                raise forms.ValidationError('Please select province, city and district.')
            if self.address_required and not address_detail:
                raise forms.ValidationError('Please enter detailed address.')

        cleaned['province'] = province
        cleaned['district'] = district
        cleaned['address_detail'] = address_detail
        return cleaned


class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ['name', 'species', 'breed', 'age', 'weight', 'gender']

    def clean_age(self):
        age = self.cleaned_data['age']
        if age < 0:
            raise forms.ValidationError('Pet age cannot be negative.')
        return age

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is not None and weight <= 0:
            raise forms.ValidationError('Pet weight must be greater than zero.')
        return weight


class PetEditForm(PetForm):
    class Meta:
        model = Pet
        fields = ['name', 'age', 'weight']


class OwnerProfileForm(AddressValidationMixin, forms.Form):
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False, max_length=20)
    province = forms.CharField(required=False, max_length=50)
    city = forms.CharField(required=False, max_length=50)
    district = forms.CharField(required=False, max_length=50)
    address_detail = forms.CharField(required=False)


class MerchantStoreForm(AddressValidationMixin, forms.Form):
    address_required = True

    store_name = forms.CharField(max_length=100)
    province = forms.CharField(max_length=50)
    city = forms.CharField(required=False, max_length=50)
    district = forms.CharField(max_length=50)
    address_detail = forms.CharField()
    contact_phone = forms.CharField(required=False, max_length=20)
    operating_hours = forms.CharField(required=False, max_length=50)
    description = forms.CharField(required=False)

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        if not (cleaned.get('store_name') or '').strip():
            raise forms.ValidationError('Please enter store name.')
        return cleaned


class ServiceForm(forms.ModelForm):
    is_vaccine_service = forms.BooleanField(required=False)

    class Meta:
        model = Service
        fields = ['name', 'category', 'description', 'price', 'is_vaccine_service']

    def __init__(self, *args, merchant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.merchant = merchant
        categories = ServiceCategory.objects.all()
        if merchant and merchant.primary_category_id:
            categories = categories.filter(id=merchant.primary_category_id)
        self.fields['category'].queryset = categories

    def clean_name(self):
        name = (self.cleaned_data['name'] or '').strip()
        qs = Service.objects.filter(merchant=self.merchant, name=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'You already have a service named "{name}". Names must be unique.')
        return name

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        if self.merchant and self.merchant.primary_category_id and category:
            if self.merchant.primary_category_id != category.id:
                raise forms.ValidationError('You can only manage services in your store category.')
        if category and not _is_medical_category(category):
            cleaned['is_vaccine_service'] = False
        return cleaned


class ReviewForm(forms.Form):
    rating = forms.IntegerField(min_value=1, max_value=5)
    comment = forms.CharField(required=False)

    def clean_comment(self):
        comment = (self.cleaned_data.get('comment') or '').strip()
        return comment or 'This user did not leave a comment.'
