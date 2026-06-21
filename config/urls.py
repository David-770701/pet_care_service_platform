from django.urls import path, include

urlpatterns = [
    path('', include('pet_services.urls')),
]
