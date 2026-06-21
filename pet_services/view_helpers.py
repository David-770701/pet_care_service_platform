import calendar
from datetime import time
from typing import Optional

from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Merchant, Service, ServiceCategory

__all__ = [
    'MUNICIPALITIES',
    'confirmed_post',
    'flash_form_errors',
    'pagination_query',
    'paginate',
    '_add_months',
    '_compose_full_address',
    '_compose_full_address_3',
    '_is_medical_category',
    '_is_medical_service',
    '_merchant_is_pending_for_review',
    '_parse_operating_hours',
    '_safe_next_url',
    '_split_full_address',
]

MUNICIPALITIES = {'\u5317\u4eac\u5e02', '\u4e0a\u6d77\u5e02', '\u5929\u6d25\u5e02', '\u91cd\u5e86\u5e02'}


def flash_form_errors(request, messages, form) -> None:
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)

def confirmed_post(request) -> bool:
    return request.method == 'POST' and request.POST.get('confirmed') == '1'

def paginate(request, queryset, per_page: int):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))

def pagination_query(request) -> str:
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()

def _compose_full_address(province: str, city: str, detail: str):
    p = (province or '').strip()
    c = (city or '').strip()
    d = (detail or '').strip()
    return ' '.join([x for x in [p, c, d] if x])

def _is_medical_category(category: Optional[ServiceCategory]) -> bool:
    name = (category.name if category else '')
    n = name.strip().lower()
    return n in {'pet medical', 'medical', 'pet medical services', 'pet medical care'} or 'medical' in n

def _parse_operating_hours(hours_text: str):
    raw = (hours_text or '').strip()
    if not raw:
        return None
    if '-' not in raw:
        return None
    left, right = [p.strip() for p in raw.split('-', 1)]
    if ':' not in left or ':' not in right:
        return None
    try:
        lh, lm = left.split(':', 1)
        rh, rm = right.split(':', 1)
        sh = int(lh)
        sm = int(lm)
        eh = int(rh)
        em = int(rm)
        if sh == 24 and sm == 0:
            sh = 0
            sm = 0
        if eh == 24 and em == 0:
            eh = 23
            em = 59
        start = time(hour=sh, minute=sm)
        end = time(hour=eh, minute=em)
    except Exception:
        return None
    return start, end

def _compose_full_address_3(province: str, city: str, district: str, detail: str):
    p = (province or '').strip()
    c = (city or '').strip()
    a = (district or '').strip()
    d = (detail or '').strip()
    return ' '.join([x for x in [p, c, a, d] if x])

def _add_months(d, months: int):
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    day = min(d.day, last_day)
    return d.replace(year=y, month=m, day=day)

def _split_full_address(full_address: str):
    raw = (full_address or '').strip()
    if not raw:
        return '', '', '', ''
    parts = raw.split()
    if len(parts) >= 4:
        return parts[0], parts[1], parts[2], ' '.join(parts[3:])
    if len(parts) == 3:
        return parts[0], parts[1], '', parts[2]
    return '', '', '', raw

def _is_medical_service(service: Service):
    return _is_medical_category(service.category)

def _merchant_is_pending_for_review(merchant: Merchant):
    return (not merchant.is_verified) and (not merchant.user.is_active)

def _safe_next_url(request, fallback_url: str):
    next_url = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER')
    if not next_url:
        return fallback_url
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback_url
