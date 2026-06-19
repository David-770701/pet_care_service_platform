from django.apps import AppConfig


class PetCoreConfig(AppConfig):
    name = 'pet_core'

    def ready(self):
        from . import signals
