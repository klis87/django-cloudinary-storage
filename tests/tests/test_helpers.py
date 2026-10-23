import hashlib
import os
import shutil
import tempfile
from io import StringIO
from unittest import mock
from uuid import uuid4

from django.contrib.staticfiles.storage import HashedFilesMixin
from django.core.files import File
from django.core.management import call_command
from django.test import override_settings

from cloudinary_storage import app_settings
from cloudinary_storage.management.commands.deleteorphanedmedia import Command as DeleteOrphanedMediaCommand
from cloudinary_storage.storage import MediaCloudinaryStorage

STYLE_PATH = os.path.join('tests', 'static', 'tests', 'css', 'style.css')
IMAGE_PATH = os.path.join('tests', 'static', 'tests', 'images', 'dummy-static-image.jpg')

LOCAL_STATIC_STORAGES = {
    'default': {'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

STATIC_HASHED_STORAGES = {
    'default': {'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage'},
    'staticfiles': {'BACKEND': 'cloudinary_storage.storage.StaticHashedCloudinaryStorage'},
}


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


def get_file_hash(path, name):
    with open(path, 'rb') as f:
        return HashedFilesMixin().file_hash(name, File(f))


def get_file_md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


STYLE_HASH = get_file_hash(STYLE_PATH, 'tests/css/style.css')
IMAGE_HASH = get_file_hash(IMAGE_PATH, 'tests/images/dummy-static-image.jpg')
STYLE_MD5 = get_file_md5(STYLE_PATH)
IMAGE_MD5 = get_file_md5(IMAGE_PATH)


class TemporaryStaticRootTestsMixin(object):
    """
    Keeps STATIC_ROOT and manifest in temporary directories, so tests running collectstatic are isolated.
    """
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.manifest_root = os.path.join(cls.temp_dir, 'manifest')
        cls.manifest_root_patcher = mock.patch.object(app_settings, 'STATICFILES_MANIFEST_ROOT', cls.manifest_root)
        cls.manifest_root_patcher.start()
        cls.static_root_override = override_settings(STATIC_ROOT=os.path.join(cls.temp_dir, 'staticfiles'))
        cls.static_root_override.enable()
        super(TemporaryStaticRootTestsMixin, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TemporaryStaticRootTestsMixin, cls).tearDownClass()
        cls.static_root_override.disable()
        cls.manifest_root_patcher.stop()
        shutil.rmtree(cls.temp_dir)


def import_mock():
    return mock
