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
        content = ContentFile(b'Content of file')
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
        response.status_code = 400
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

    @classmethod
    def tearDownClass(cls):
        cls.storage.delete(cls.file_name)
