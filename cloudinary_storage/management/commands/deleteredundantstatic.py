import cloudinary.uploader
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import CommandError

from cloudinary_storage import app_settings
from cloudinary_storage.storage import StaticHashedCloudinaryStorage, RESOURCE_TYPES
from . import deleteorphanedmedia


class Command(deleteorphanedmedia.Command):
    help = 'Removes redundant static files'
    TAG = app_settings.STATIC_TAG

    @property
    def storage(self):
        return staticfiles_storage

    def get_resource_types(self):
        """
        Overwritten as static files can be of any resource type.
        """
        return set(RESOURCE_TYPES.values())

    def get_exclude_paths(self):
        return ()

    def get_needful_files(self):
        """
        Returns currently used static files.
        Assumes that manifest staticfiles.json is up-to-date.
        """
        paths, _ = self.storage.load_manifest()
        needful_files = set(paths.values())
        if app_settings.UPLOAD_UNHASHED_STATIC_FILES:
            needful_files.update(paths.keys())
        return {self.storage._get_public_id(file) for file in needful_files}

    def delete_orphaned_files(self, files):
        """
        Overwritten as static storage keeps files locally, they are deleted directly from Cloudinary.
        """
        for resource_type, files_per_type in files.items():
            for file in files_per_type:
                cloudinary.uploader.destroy(file, invalidate=True, resource_type=resource_type)
                self.stdout.write('Deleted {}.'.format(file))

    def handle(self, *args, **options):
        if not isinstance(self.storage, StaticHashedCloudinaryStorage):
            raise CommandError('Command requires StaticHashedCloudinaryStorage as staticfiles storage.')
        if self.storage.read_manifest() is None:
            raise CommandError('Command requires staticfiles.json. Run collectstatic command first and try again.')
        super(Command, self).handle(*args, **options)
