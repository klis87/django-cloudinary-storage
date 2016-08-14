from django.core.management import CommandError
from django.utils.six import PY3

from cloudinary_storage.storage import StaticHashedCloudinaryStorage, RESOURCE_TYPES
from cloudinary_storage import app_settings
from . import deleteorphanedmedia


class Command(deleteorphanedmedia.Command):
    help = 'Removes redundant static files'
    storage = StaticHashedCloudinaryStorage()
    TAG = app_settings.STATIC_TAG

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--delete-unhashed-files', action='store_true', dest='delete_unhashed_files',
                            help='Delete needless unhashed files as well. '
                                 'Use only when you used collectstatic with --upload-unhashed-files option.')

    def set_options(self, **options):
        super(Command, self).set_options(**options)
        self.delete_unhashed_files = options['delete_unhashed_files']

    def get_resource_types(self):
        return {RESOURCE_TYPES['RAW']}

    def get_exclude_paths(self):
        return ()

    def get_needful_files(self):
        manifest = self.storage.load_manifest()
        if self.delete_unhashed_files:
            return set(manifest.values())
        else:
            if PY3:
                needful_files = set(manifest.keys() | manifest.values())
            else:
                needful_files = set(manifest.keys() + manifest.values())
            return {self.storage.clean_name(file) for file in needful_files}

    def handle(self, *args, **options):
        if self.storage.read_manifest() is None:
            raise CommandError('Command requires staticfiles.json. Run collectstatic first and try again.')
        super(Command, self).handle(*args, **options)
