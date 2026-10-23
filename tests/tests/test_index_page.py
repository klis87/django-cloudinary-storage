from django.test import SimpleTestCase, override_settings

from cloudinary_storage.storage import StaticHashedCloudinaryStorage
from tests.tests.test_helpers import (execute_command, import_mock, TemporaryStaticRootTestsMixin, STATIC_STORAGES,
                                      STATIC_HASHED_STORAGES, STYLE_HASH, IMAGE_HASH)

mock = import_mock()


@override_settings(STORAGES=STATIC_STORAGES)
class IndexPageTestsWithUnhashedStaticStorageTests(SimpleTestCase):
    @override_settings(DEBUG=True)
    def test_urls_with_debug_true(self):
        response = self.client.get('/')
        self.assertContains(response, '"/static/tests/css/style.css"')

    def test_urls_with_debug_false(self):
        response = self.client.get('/')
        self.assertContains(response, '/raw/upload/v1/static/tests/css/style.css')

    def test_cloudinary_static_tag(self):
        response = self.client.get('/')
        self.assertContains(response, '/image/upload/h_50,w_50/v1/static/tests/images/dummy-static-image.jpg')


@override_settings(STORAGES=STATIC_HASHED_STORAGES)
class IndexPageTestsWithStaticHashedStorageTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super(IndexPageTestsWithStaticHashedStorageTests, cls).setUpClass()
        with mock.patch('cloudinary_storage.storage.get_resources_md5_by_prefix', return_value={}):
            with mock.patch('cloudinary_storage.storage.cloudinary.uploader.upload'):
                execute_command('collectstatic', '--noinput')

    @override_settings(DEBUG=True)
    def test_urls_with_debug_true(self):
        response = self.client.get('/')
        self.assertContains(response, '"/static/tests/css/style.css"')

    def test_urls_with_debug_false(self):
        response = self.client.get('/')
        self.assertContains(response, '/raw/upload/v1/static/tests/css/style.{}.css'.format(STYLE_HASH))
        self.assertContains(response, '/image/upload/v1/static/tests/images/dummy-static-image.{}.jpg'.format(
            IMAGE_HASH))

    def test_cloudinary_static_tag(self):
        response = self.client.get('/')
        self.assertContains(response, '/image/upload/h_50,w_50/v1/static/tests/images/dummy-static-image.{}.jpg'.format(
            IMAGE_HASH))

    @mock.patch.object(StaticHashedCloudinaryStorage, 'hashed_name')
    def test_manifest_is_used_in_production(self, hashed_name_mock):
        self.client.get('/')
        self.assertFalse(hashed_name_mock.called)
