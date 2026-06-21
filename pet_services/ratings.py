from django.db.models import Avg

from .models import Merchant, Review


def _chunked(items: list[int], size: int):
    for idx in range(0, len(items), size):
        yield items[idx:idx + size]


def recalc_merchant_average_rating(merchant_id: int) -> None:
    avg = (
        Review.objects.filter(order__service__merchant_id=merchant_id)
        .aggregate(a=Avg('rating'))
        .get('a')
    )
    Merchant.objects.filter(user_id=merchant_id).update(average_rating=avg or 0)


def bulk_recalc_merchant_average_rating(merchant_ids: list[int]) -> None:
    merchant_ids = [int(x) for x in merchant_ids if x is not None]
    if not merchant_ids:
        return

    for chunk in _chunked(merchant_ids, 800):
        qs = (
            Review.objects.filter(order__service__merchant_id__in=chunk)
            .values('order__service__merchant_id')
            .annotate(a=Avg('rating'))
        )
        avg_by_mid = {row['order__service__merchant_id']: row['a'] for row in qs}
        updates = []
        for mid in chunk:
            updates.append(Merchant(user_id=mid, average_rating=avg_by_mid.get(mid) or 0))
        Merchant.objects.bulk_update(updates, ['average_rating'], batch_size=800)
