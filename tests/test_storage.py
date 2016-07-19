from uuid import uuid4
from unittest import mock

from requests.exceptions import HTTPError

from django.test import SimpleTestCase
from django.core.files.base import ContentFile

from cloudinary_storage.storage import MediaCloudinaryStorage


def get_random_name():
    return str(uuid4())

TAG = get_random_name()


class CloudinaryMediaStorageTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage = MediaCloudinaryStorage(tag=TAG, resource_type='raw')
        cls.file_name, cls.file = cls.upload_file()

    @classmethod
    def upload_file(cls):
        file_name = get_random_name()
        cls.file_content = b'Content of file'
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

    @classmethod
    def tearDownClass(cls):
        cls.storage.delete(cls.file_name)
