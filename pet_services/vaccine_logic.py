from datetime import timedelta

from django.utils import timezone


SPECIES_ALIASES = {
    'dog': 'Dog',
    '狗': 'Dog',
    '犬': 'Dog',
    'cat': 'Cat',
    '猫': 'Cat',
    'rabbit': 'Rabbit',
    '兔': 'Rabbit',
    '兔子': 'Rabbit',
    'hedgehog': 'Hedgehog',
    '刺猬': 'Hedgehog',
    'snake': 'Snake',
    '蛇': 'Snake',
    'turtle': 'Turtle',
    '乌龟': 'Turtle',
    '龟': 'Turtle',
    'hamster': 'Hamster',
    '仓鼠': 'Hamster',
    'ferret': 'Ferret',
    '雪貂': 'Ferret',
}


def normalize_species_name(raw: str) -> str:
    key = (raw or '').strip()
    if not key:
        return ''
    return SPECIES_ALIASES.get(key.lower(), SPECIES_ALIASES.get(key, key))


def infer_animal_type_from_vaccine_name(vaccine_name: str, full_name: str = '') -> str:
    text = f'{vaccine_name or ""} {full_name or ""}'
    if any(token in text for token in ('犬', '狗')):
        return 'Dog'
    if '猫' in text:
        return 'Cat'
    if any(token in text for token in ('兔', '巴氏杆菌')):
        return 'Rabbit'
    if '刺猬' in text:
        return 'Hedgehog'
    if '蛇' in text:
        return 'Snake'
    if any(token in text for token in ('白眼病', '腐甲病', '龟')):
        return 'Turtle'
    if '仓鼠' in text:
        return 'Hamster'
    if '雪貂' in text:
        return 'Ferret'
    return ''


def calculate_next_due_date(vaccine, administered_date):
    if vaccine is None or administered_date is None:
        return None
    if vaccine.is_booster:
        return administered_date + timedelta(days=365)
    if vaccine.dose_number < vaccine.total_basic_doses:
        return administered_date + timedelta(days=21)
    return administered_date + timedelta(days=365)


def get_species_vaccine_queryset(VaccineModel, species: str):
    animal_type = normalize_species_name(species)
    if not animal_type:
        return VaccineModel.objects.none()
    return VaccineModel.objects.filter(animal_type=animal_type).order_by(
        'vaccine_name',
        'dose_number',
        'v_id',
    )


def get_pet_vaccine_queryset(VaccineModel, pet):
    animal_type = normalize_species_name(getattr(pet, 'species', ''))
    if not animal_type:
        return VaccineModel.objects.none()
    return VaccineModel.objects.filter(animal_type=animal_type).order_by(
        'vaccine_name',
        'dose_number',
        'v_id',
    )


def build_due_vaccine_reminders(owner):
    today = timezone.now().date()
    reminder_items = []
    seen_series = set()

    records = (
        owner.pets.select_related()
        .prefetch_related('vaccines__vaccine')
    )
    for pet in records:
        latest_records = pet.vaccines.select_related('vaccine').order_by('-administered_date', '-id')
        for record in latest_records:
            vaccine = record.vaccine
            if vaccine is None:
                continue
            key = (pet.id, vaccine.series_id)
            if key in seen_series:
                continue
            seen_series.add(key)
            if vaccine.is_booster:
                continue
            if record.next_due_date is None:
                continue
            days_left = (record.next_due_date - today).days
            if 0 <= days_left <= 3:
                reminder_items.append({
                    'pet': pet,
                    'record': record,
                    'series_id': vaccine.series_id,
                    'series_name': vaccine.vaccine_name,
                    'next_vaccine_name': _describe_next_vaccine(vaccine),
                    'days_left': days_left,
                })
            break
    reminder_items.sort(key=lambda item: (item['record'].next_due_date, item['pet'].name))
    return reminder_items


def _describe_next_vaccine(vaccine):
    if vaccine is None:
        return ''
    if vaccine.is_booster:
        return '年度加强针'
    if vaccine.dose_number < vaccine.total_basic_doses:
        return f'第{vaccine.dose_number + 1}针基础免疫'
    return '年度加强针'
