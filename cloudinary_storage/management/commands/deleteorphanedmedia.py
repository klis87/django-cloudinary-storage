from itertools import chain

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models

from cloudinary_storage.helpers import get_resources
from cloudinary_storage.storage import storages_per_type
from cloudinary_storage import app_settings


class Command(BaseCommand):
    help = 'Removes all orphaned media files'

    def models(self):
        return apps.get_models()

    def model_file_fields(self, model):
        for field in model._meta.fields:
            if isinstance(field, models.FileField):
                yield field

    def get_resource_types(self):
        media_types = set()
        for model in self.models():
            for field in self.model_file_fields(model):
                media_type = field.storage.RESOURCE_TYPE
                media_types.add(media_type)
        return media_types

    def get_uploaded_media(self):
        uploaded_media = []
        for model in self.models():
            media_fields = []
            for field in self.model_file_fields(model):
                media_fields.append(field.name)
            if media_fields:
                exclude_options = {media_field: '' for media_field in media_fields}
                model_uploaded_media = model.objects.exclude(**exclude_options).values_list(*media_fields)
                uploaded_media.extend(model_uploaded_media)
        return set(chain.from_iterable(uploaded_media))

    def get_files_to_remove(self):
        files_to_remove = {}
        uploaded_media = self.get_uploaded_media()
        for resources_type in self.get_resource_types():
            resources = set(get_resources(resources_type, app_settings.MEDIA_TAG))
            files_to_remove[resources_type] = resources - uploaded_media
        return files_to_remove
