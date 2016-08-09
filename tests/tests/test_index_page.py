from unittest import mock
import os

from django.test import SimpleTestCase, override_settings
from django.core.files import File
from django.contrib.staticfiles.storage import HashedFilesMixin

from cloudinary_storage import app_settings
from cloudinary_storage.storage import StaticHashedCloudinaryStorage
from tests.tests.test_helpers import get_random_name, execute_command


@override_settings(STATICFILES_STORAGE='cloudinary_storage.storage.StaticCloudinaryStorage')
class IndexPageTestsWithUnhashedStaticStorageTests(SimpleTestCase):
    @override_settings(DEBUG=True)
    def test_urls_with_debug_true(self):
        response = self.client.get('/')
        self.assertContains(response, '/static/tests/css/style.css')

    def test_urls_with_debug_false(self):
        response = self.client.get('/')
        self.assertContains(response, '/raw/upload/v1/tests/css/style.css')


DEFAULT_MANIFEST_ROOT = app_settings.STATICFILES_MANIFEST_ROOT


class StaticHashedStorageTestsMixin(object):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        hash_mixin = HashedFilesMixin()
        content = File(open('tests/static/tests/css/style.css', 'rb'))
        cls.style_hash = hash_mixin.file_hash('tests/css/style.css', content)
        content.close()
        content = File(open('tests/static/tests/css/font.css', 'rb'))
        cls.font_hash = hash_mixin.file_hash('tests/css/font.css', content)
        content.close()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        app_settings.STATICFILES_MANIFEST_ROOT = DEFAULT_MANIFEST_ROOT


@override_settings(STATICFILES_STORAGE='cloudinary_storage.storage.StaticHashedCloudinaryStorage')
class IndexPageTestsWithStaticHashedStorageTests(StaticHashedStorageTestsMixin, SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        app_settings.STATICFILES_MANIFEST_ROOT = 'manifest-' + get_random_name()
        super().setUpClass()

    @override_settings(DEBUG=True)
    def test_urls_with_debug_true(self):
        response = self.client.get('/')
        self.assertContains(response, '/static/tests/css/style.css')

    def test_urls_with_debug_false(self):
        response = self.client.get('/')
        self.assertContains(response, '/raw/upload/v1/tests/css/style.{}.css'.format(self.style_hash))


@override_settings(STATICFILES_STORAGE='cloudinary_storage.storage.StaticHashedCloudinaryStorage')
class IndexPageTestsWithStaticHashedStorageWithManifestTests(StaticHashedStorageTestsMixin, SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        app_settings.STATICFILES_MANIFEST_ROOT = 'manifest-' + get_random_name()
        with mock.patch.object(StaticHashedCloudinaryStorage, '_upload'):
            execute_command('collectstatic', '--noinput')
            cls.manifest_path = os.path.join(app_settings.STATICFILES_MANIFEST_ROOT, 'staticfiles.json')
            with open(cls.manifest_path) as f:
                cls.manifest = f.read()
        super().setUpClass()

    def test_urls_with_debug_false(self):
        response = self.client.get('/')
        self.assertContains(response, '/raw/upload/v1/tests/css/style.{}.css'.format(self.style_hash))

    @mock.patch.object(StaticHashedCloudinaryStorage, 'hashed_name')
    def test_manifest_is_used_in_production(self, hashed_name_mock):
        self.client.get('/')
        self.assertFalse(hashed_name_mock.called)

    def test_manifest_has_correct_content(self):
        self.assertIn('tests/css/style.css', self.manifest)
        self.assertIn('tests/css/style.{}.css'.format(self.style_hash), self.manifest)
        self.assertIn('tests/css/font.css', self.manifest)
        self.assertIn('tests/css/font.{}.css'.format(self.font_hash), self.manifest)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.manifest_path)
        os.rmdir(app_settings.STATICFILES_MANIFEST_ROOT)
        super().tearDownClass()
