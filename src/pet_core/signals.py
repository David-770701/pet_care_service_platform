from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import Review
from .ratings import recalc_merchant_average_rating


@receiver(pre_delete, sender=Review)
def review_pre_delete(sender, instance: Review, **kwargs):
    merchant_id = None
    try:
        merchant_id = instance.order.service.merchant_id
    except Exception:
        merchant_id = None
    instance._merchant_id = merchant_id


@receiver(post_save, sender=Review)
def review_post_save(sender, instance: Review, **kwargs):
    merchant_id = None
    try:
        merchant_id = instance.order.service.merchant_id
    except Exception:
        merchant_id = getattr(instance, '_merchant_id', None)
    if merchant_id is not None:
        recalc_merchant_average_rating(int(merchant_id))


@receiver(post_delete, sender=Review)
def review_post_delete(sender, instance: Review, **kwargs):
    merchant_id = getattr(instance, '_merchant_id', None)
    if merchant_id is not None:
        recalc_merchant_average_rating(int(merchant_id))
