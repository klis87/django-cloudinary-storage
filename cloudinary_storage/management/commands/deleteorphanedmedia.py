from itertools import chain

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models

from cloudinary_storage.helpers import get_resources
from cloudinary_storage.storage import storages_per_type
from cloudinary_storage import app_settings


class Command(BaseCommand):
    help = 'Removes all orphaned media files'

    def add_arguments(self, parser):
        parser.add_argument('--noinput', action='store_true', dest='noinput',
                            help='Do not prompt the user for input of any kind.')

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

    def get_flattened_files_to_remove(self, files):
        result = set()
        for files_per_type in files.values():
            result = result | files_per_type
        return result

    def delete_orphaned_files(self, files):
        for resource_type, files_per_type in files.items():
            for file in files_per_type:
                storages_per_type[resource_type].delete(file)

    def handle(self, *args, **options):
        files_to_remove = self.get_files_to_remove()
        flattened_files_to_remove = self.get_flattened_files_to_remove(files_to_remove)
        length = len(flattened_files_to_remove)
        files_to_remove_str = '\n- '.join(flattened_files_to_remove)
        if not length:
            self.stdout.write('There is no file to delete.')
            return
        self.stdout.write('{} files will be deleted:\n- {}'.format(length, files_to_remove_str))
        if options['noinput'] or input("If you are sure to delete them, please type 'yes': ") == 'yes':
            self.delete_orphaned_files(files_to_remove)
            self.stdout.write('{} files have been deleted successfully.'.format(length))
        else:
            self.stdout.write('As ordered, no file has been deleted.')
