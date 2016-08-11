from django.contrib.staticfiles.management.commands import collectstatic
from django.conf import settings


class Command(collectstatic.Command):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--upload-unhashed-files', action='store_true', dest='upload_unhashed_files',
                            help='Apart from hashed files, upload unhashed ones as well. Use only when you need it.')

    def set_options(self, **options):
        super(Command, self).set_options(**options)
        self.upload_unhashed_files = options['upload_unhashed_files']

    def delete_file(self, path, prefixed_path, source_storage):
        return True

    def copy_file(self, path, prefixed_path, source_storage):
        if (settings.STATICFILES_STORAGE == 'cloudinary_storage.storage.StaticCloudinaryStorage' or
                self.upload_unhashed_files):
            super(Command, self).copy_file(path, prefixed_path, source_storage)
