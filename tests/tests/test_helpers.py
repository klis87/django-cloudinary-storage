from uuid import uuid4
import os
import errno

from django.contrib.staticfiles.storage import HashedFilesMixin
from django.core.files import File
from django.core.management import call_command
from django.utils.six import StringIO

from cloudinary_storage import app_settings
from cloudinary_storage.storage import MediaCloudinaryStorage, StaticHashedCloudinaryStorage
from cloudinary_storage.management.commands.deleteorphanedmedia import Command as DeleteOrphanedMediaCommand


def get_random_name():
    return str(uuid4())


def set_media_tag(tag):
    MediaCloudinaryStorage.TAG = tag
    DeleteOrphanedMediaCommand.TAG = tag
    app_settings.MEDIA_TAG = tag


def execute_command(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


class StaticHashedStorageTestsMixin(object):
    @classmethod
    def setUpClass(cls):
        StaticHashedCloudinaryStorage.manifest_name = get_random_name()
        hash_mixin = HashedFilesMixin()
        content = File(open(os.path.join('tests', 'static', 'tests', 'css', 'style.css'), 'rb'))
        cls.style_hash = hash_mixin.file_hash('tests/css/style.css', content)
        content.close()
        content = File(open(os.path.join('tests', 'static', 'tests', 'css', 'font.css'), 'rb'))
        cls.font_hash = hash_mixin.file_hash('tests/css/font.css', content)
        content.close()
        content = File(open(os.path.join('tests', 'static', 'tests', 'images', 'dummy-static-image.jpg'), 'rb'))
        cls.image_hash = hash_mixin.file_hash('tests/images/dummy-static-image.jpg', content)
        content.close()
        name = StaticHashedCloudinaryStorage.manifest_name
        cls.manifest_path = os.path.join(app_settings.STATICFILES_MANIFEST_ROOT, name)
        super(StaticHashedStorageTestsMixin, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(cls.manifest_path)
        except (IOError, OSError) as e:
            if e.errno != errno.ENOENT:
                raise
        super(StaticHashedStorageTestsMixin, cls).tearDownClass()
        StaticHashedCloudinaryStorage.manifest_name = 'staticfiles.json'


def import_mock():
    try:
        from unittest import mock
    except ImportError:
        import mock
    finally:
        return mock
