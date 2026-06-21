from .models import ServiceCategory


def service_categories(request):
    return {
        'service_categories': ServiceCategory.objects.all().order_by('name', 'id')
    }
