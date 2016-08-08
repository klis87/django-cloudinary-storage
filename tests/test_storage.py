from unittest import mock
import os.path

from requests.exceptions import HTTPError
from django.test import SimpleTestCase, override_settings
from django.core.files.base import ContentFile
from django.conf import settings

from cloudinary_storage.storage import MediaCloudinaryStorage, ManifestCloudinaryStorage, StaticCloudinaryStorage
from cloudinary_storage import app_settings
from tests.test_helpers import get_random_name

TAG = get_random_name()


class CloudinaryMediaStorageTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.file_content = b'Content of file'
        cls.storage = MediaCloudinaryStorage(tag=TAG, resource_type='raw')
        cls.file_name, cls.file = cls.upload_file()

    @classmethod
    def upload_file(cls, prefix=''):
        file_name = prefix + get_random_name()
        content = ContentFile(cls.file_content)
        file_name = cls.storage.save(file_name, content)
        return file_name, content

    def test_file_exists_after_upload(self):
        self.assertTrue(self.storage.exists(self.file_name))

    def test_file_doesnt_exist_without_upload(self):
        file_name = get_random_name()
        self.assertFalse(self.storage.exists(file_name))

    def test_file_doesnt_exists_after_deletion(self):
        file_name, file = self.upload_file()
        self.storage.delete(file_name)
        self.assertFalse(self.storage.exists(file_name))

    @mock.patch('cloudinary_storage.storage.requests.head')
    def test_exists_raises_http_error(self, head_mock):
        response = head_mock.return_value
        response.status_code = 500
        response.raise_for_status.side_effect = HTTPError
        with self.assertRaises(HTTPError):
            self.storage.exists(get_random_name())

    def test_delete_returns_true_when_file_existed(self):
        file_name, file = self.upload_file()
        self.assertTrue(self.storage.delete(file_name))

    def test_delete_returns_false_when_file_didnt_exist(self):
        file_name = get_random_name()
        self.assertFalse(self.storage.delete(file_name))

    def test_url(self):
        url = self.storage.url('name')
        self.assertTrue(url.startswith('http'))

    def test_opened_file_has_correct_content(self):
        file = self.storage.open(self.file_name)
        self.assertEqual(file.read(), self.file_content)

    def test_opening_not_existing_file_raises_error(self):
        with self.assertRaises(IOError):
            self.storage.open('name')

    @mock.patch('cloudinary_storage.storage.requests.get')
    def test_opening_when_cloudinary_fails_raises_error(self, get_mock):
        response = get_mock.return_value
        response.status_code = 500
        response.raise_for_status.side_effect = HTTPError
        with self.assertRaises(IOError):
            self.storage.open('name')

    def test_get_available_name(self):
        name = 'name'
        available_name = self.storage.get_available_name(name)
        self.assertEqual(name, available_name)

    def test_get_available_name_with_max_length(self):
        name = 'name'
        available_name = self.storage.get_available_name(name, 2)
        self.assertEqual('na', available_name)

    def test_get_available_name_with_max_length_bigger_than_name_length(self):
        name = 'name'
        available_name = self.storage.get_available_name(name, 10)
        self.assertEqual(name, available_name)

    def test_list_dir(self):
        file_2_name, file_2 = self.upload_file(prefix='folder/')
        file_3_name, file_3 = self.upload_file(prefix='folder/subfolder/')
        try:
            self.assertEqual(self.storage.listdir(''), (['folder'], [self.file_name]))
            file_2_tail = file_2_name.replace('folder/', '', 1)
            self.assertEqual(self.storage.listdir('folder'),
                             (['subfolder'], [file_2_tail]))
            file_3_tail = file_3_name.replace('folder/subfolder/', '', 1)
            self.assertEqual(self.storage.listdir('folder/subfolder'), ([], [file_3_tail]))
        finally:
            self.storage.delete(file_2_name)
            self.storage.delete(file_3_name)

    @classmethod
    def tearDownClass(cls):
        cls.storage.delete(cls.file_name)


class ManifestCloudinaryStorageTests(SimpleTestCase):
    def test_manifest_is_saved_to_proper_location(self):
        storage = ManifestCloudinaryStorage()
        file = ContentFile(b'Dummy manifest')
        name = 'name'
        storage.save(name, file)
        expected_path = os.path.join(app_settings.STATICFILES_MANIFEST_ROOT, name)
        try:
            self.assertTrue(os.path.exists(expected_path))
        finally:
            try:
                os.remove(expected_path)
            except FileNotFoundError:
                pass


class StaticCloudinaryStorageTests(SimpleTestCase):
    @override_settings(DEBUG=True)
    def test_url_with_debug_true(self):
        storage = StaticCloudinaryStorage()
        self.assertIn(settings.STATIC_URL, storage.url('name'))

    def test_url_with_debug_false(self):
        storage = StaticCloudinaryStorage()
        self.assertIn('cloudinary', storage.url('name'))
