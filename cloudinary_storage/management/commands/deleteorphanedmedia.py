from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models

from cloudinary_storage import app_settings


class Command(BaseCommand):
    help = 'Removes all orphaned media files'

    def get_resource_types(self):
        media_types = set()
        model_list = apps.get_models()
        for model in model_list:
            for field in model._meta.fields:
                if isinstance(field, models.FileField):
                    media_type = field.storage.RESOURCE_TYPE
                    media_types.add(media_type)
        return media_types
