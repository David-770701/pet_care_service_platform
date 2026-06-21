from django.apps import AppConfig


class PetServicesConfig(AppConfig):
    name = 'pet_services'
    label = 'pet_core'

    def ready(self):
        from . import signals
