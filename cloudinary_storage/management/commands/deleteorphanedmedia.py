from itertools import chain

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

from cloudinary_storage import app_settings
from cloudinary_storage.helpers import get_resources
from cloudinary_storage.storage import storages_per_type, RESOURCE_TYPES


class Command(BaseCommand):
    help = 'Removes all orphaned media files'
    TAG = app_settings.MEDIA_TAG

    def add_arguments(self, parser):
        parser.add_argument('--noinput', action='store_true', dest='no_input',
                            help='Do not prompt the user for input of any kind.')

    def set_options(self, **options):
        self.no_input = options['no_input']

    def models(self):
        """
        Gets all registered models.
        """
        return apps.get_models()

    def model_file_fields(self, model):
        """
        Generator yielding all instances of FileField and its subclasses of a model.
        """
        for field in model._meta.fields:
            if isinstance(field, models.FileField):
                yield field

    def get_resource_types(self):
        """
        Returns set of resource types of FileFields of all registered models.
        Needed by Cloudinary as resource type is needed to browse or delete specific files.
        """
        resource_types = set()
        for model in self.models():
            for field in self.model_file_fields(model):
                resource_type = field.storage.RESOURCE_TYPE
                resource_types.add(resource_type)
        return resource_types

    def get_needful_files(self):
        """
        Returns set of media files associated with models.
        Those files won't be deleted.
        """
        needful_files = []
        for model in self.models():
            media_fields = []
            for field in self.model_file_fields(model):
                media_fields.append(field.name)
            if media_fields:
                exclude_options = {media_field: '' for media_field in media_fields}
                model_uploaded_media = model.objects.exclude(**exclude_options).values_list(*media_fields)
                needful_files.extend(model_uploaded_media)
        return set(chain.from_iterable(needful_files))

    def get_exclude_paths(self):
        storage = storages_per_type[RESOURCE_TYPES['RAW']]
        paths = [storage._prepend_prefix(path) for path in app_settings.EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS]
        return tuple(paths)

    def get_files_to_remove(self):
        """
        Returns orphaned media files to be removed grouped by resource type.
        All files which paths start with any of exclude paths are ignored.
        """
        files_to_remove = {}
        needful_files = self.get_needful_files()
        for resources_type, resources in self.get_uploaded_resources():
            exclude_paths = self.get_exclude_paths()
            resources = {resource for resource in resources if not resource.startswith(exclude_paths)}
            files_to_remove[resources_type] = resources - needful_files
        return files_to_remove

    def get_uploaded_resources(self):
        for resources_type in self.get_resource_types():
            resources = get_resources(resources_type, self.TAG)
            yield resources_type, resources

    def get_flattened_files_to_remove(self, files):
        result = set()
        for files_per_type in files.values():
            result = result | files_per_type
        return result

    def delete_orphaned_files(self, files):
        for resource_type, files_per_type in files.items():
            for file in files_per_type:
                self.get_file_storage(resource_type).delete(file)
                self.stdout.write('Deleted {}.'.format(file))

    def get_file_storage(self, resource_type):
        return storages_per_type[resource_type]

    def handle(self, *args, **options):
        self.set_options(**options)
        files_to_remove = self.get_files_to_remove()
        flattened_files_to_remove = self.get_flattened_files_to_remove(files_to_remove)
        length = len(flattened_files_to_remove)
        files_to_remove_str = '\n- '.join(flattened_files_to_remove)
        if not length:
            self.stdout.write('There is no file to delete.')
            return
        self.stdout.write('{} files will be deleted:\n- {}'.format(length, files_to_remove_str))
        if self.no_input or input("If you are sure to delete them, please type 'yes': ") == 'yes':
            self.delete_orphaned_files(files_to_remove)
            self.stdout.write('{} files have been deleted successfully.'.format(length))
        else:
            self.stdout.write('As ordered, no file has been deleted.')
