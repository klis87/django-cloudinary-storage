import errno
import os.path

from requests.exceptions import HTTPError
import cloudinary.uploader
from django.test import SimpleTestCase, override_settings
from django.core.files.base import ContentFile
from django.conf import settings

from cloudinary_storage.storage import (MediaCloudinaryStorage, ManifestCloudinaryStorage, StaticCloudinaryStorage,
                                        StaticHashedCloudinaryStorage, RESOURCE_TYPES)
from cloudinary_storage import app_settings
from tests.tests.test_helpers import get_random_name, import_mock

mock = import_mock()

TAG = get_random_name()


class CloudinaryMediaStorageTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super(CloudinaryMediaStorageTests, cls).setUpClass()
        cls.file_content = b'Content of file'
        cls.storage = MediaCloudinaryStorage(tag=TAG, resource_type='raw')
        cls.file_name, cls.file = cls.upload_file()

    @classmethod
    def upload_file(cls, prefix='', directory_name=''):
        file_name = prefix + directory_name + get_random_name()
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

    def test_size_of_existing_file(self):
        size = self.storage.size(self.file_name)
        self.assertEqual(size, self.file.size)

    def test_size_of_not_existing_file_returns_none(self):
        file_name = get_random_name()
        size = self.storage.size(file_name)
        self.assertEqual(size, None)

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
        try:
            self.assertEqual(self.storage.listdir(''), (['media'], []))
            file_1_tail = self.file_name.replace('media/', '', 1)
            self.assertEqual(self.storage.listdir('media/'), (['folder'], [file_1_tail]))
            file_2_tail = file_2_name.replace('media/folder/', '', 1)
            self.assertEqual(self.storage.listdir('media/folder'),
                             ([], [file_2_tail]))
        finally:
            self.storage.delete(file_2_name)

    def test_file_with_windows_path_uploaded_and_exists(self):
        file_name, file = self.upload_file(directory_name='windows\\styled\\path\\')
        try:
            self.assertTrue(self.storage.exists(file_name))
        finally:
            self.storage.delete(file_name)

    def test_prefix_configuration(self):
        with override_settings(CLOUDINARY_STORAGE={'PREFIX': 'test/prefix'}):
            self.assertEqual(self.storage._get_prefix(), 'test/prefix')
            self.assertTrue(self.storage._prepend_prefix('filename').startswith('test/prefix'))

    @classmethod
    def tearDownClass(cls):
        super(CloudinaryMediaStorageTests, cls).tearDownClass()
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
            except (IOError, OSError) as e:
                if e.errno != errno.ENOENT:
                    raise


class StaticCloudinaryStorageTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super(StaticCloudinaryStorageTests, cls).setUpClass()
        cls.storage = StaticCloudinaryStorage(tag=get_random_name())
        name = get_random_name()
        cls.content = b'some content'
        cls.file = ContentFile(cls.content)
        cls.name = cls.storage.save(name, cls.file)

    @override_settings(DEBUG=True)
    def test_url_with_debug_true(self):
        self.assertIn(settings.STATIC_URL, self.storage.url('name'))

    def test_url_with_debug_false(self):
        self.assertIn('cloudinary', self.storage.url('name'))

    def test_file_exists_with_the_same_name_as_before_save(self):
        self.assertTrue(self.storage.exists(self.name))

    @mock.patch.object(MediaCloudinaryStorage, '_save')
    def test_file_wont_be_uploaded_with_the_same_content(self, save_mock):
        self.storage.save(self.name, self.file)
        self.assertFalse(save_mock.called)

    @mock.patch.object(MediaCloudinaryStorage, '_save')
    def test_file_will_be_uploaded_with_different_content(self, save_mock):
        changed_file = ContentFile(b'changed content')
        self.storage.save(self.name, changed_file)
        save_mock.assert_called_once_with(self.name, changed_file)

    def test_get_file_extension_returns_none_for_file_without_extension(self):
        extension = self.storage._get_file_extension('file-with-accidental-ending-jpg')
        self.assertIsNone(extension)

    def test_get_file_extension_returns_correct_file_extension(self):
        extension = self.storage._get_file_extension('file.png.jpg')
        self.assertEqual(extension, 'jpg')

    def test_get_file_extension_converts_extension_to_lowercase(self):
        extension = self.storage._get_file_extension('file.JPG')
        self.assertEqual(extension, 'jpg')

    def test_get_resource_type_returns_default_resource_type_for_file_without_extension(self):
        resource_type = self.storage._get_resource_type('file-without-extension')
        self.assertEqual(resource_type, self.storage.RESOURCE_TYPE)

    def test_get_resource_type_returns_default_resource_type_for_file_with_js_extension(self):
        resource_type = self.storage._get_resource_type('file.js')
        self.assertEqual(resource_type, self.storage.RESOURCE_TYPE)

    def test_get_resource_type_returns_image_resource_type_for_file_with_jpg_extension(self):
        resource_type = self.storage._get_resource_type('file.jpg')
        self.assertEqual(resource_type, RESOURCE_TYPES['IMAGE'])

    def test_get_resource_type_returns_video_resource_type_for_file_with_avi_extension(self):
        resource_type = self.storage._get_resource_type('file.avi')
        self.assertEqual(resource_type, RESOURCE_TYPES['VIDEO'])

    def test_remove_extension_for_non_raw_file_leaves_name_intact_when_raw_file(self):
        name = self.storage._remove_extension_for_non_raw_file('file.css')
        self.assertEqual(name, 'file.css')

    def test_remove_extension_for_non_raw_file_leaves_name_intact_when_file_without_extension(self):
        name = self.storage._remove_extension_for_non_raw_file('file')
        self.assertEqual(name, 'file')

    def test_remove_extension_for_non_raw_file_removes_extension_when_file_is_jpg(self):
        name = self.storage._remove_extension_for_non_raw_file('file.jpg')
        self.assertEqual(name, 'file')

    @mock.patch.object(cloudinary.uploader, 'upload')
    def test_upload_uses_remove_extension_for_non_raw_file(self, cloudinary_upload_mock):
        self.storage._upload('name.jpg', 'content')
        resource_type = self.storage._get_resource_type('name.jpg')
        cloudinary_upload_mock.assert_called_once_with('content', public_id='name', resource_type=resource_type,
                                                       invalidate=True, tags=self.storage.TAG)

    @classmethod
    def tearDownClass(cls):
        super(StaticCloudinaryStorageTests, cls).tearDownClass()
        cls.storage.delete(cls.name)


class StaticHashedCloudinaryStorageTests(SimpleTestCase):
    @mock.patch('cloudinary_storage.storage.finders.find')
    def test_hashed_name_raises_error_when_file_not_found(self, find_mock):
        storage = StaticHashedCloudinaryStorage()
        not_existing_file = get_random_name()
        find_mock.return_value = not_existing_file
        with self.assertRaises(ValueError):
            storage.hashed_name(not_existing_file)

    def test_existing_manifest_is_deleted_before_new_is_saved(self):
        storage = StaticHashedCloudinaryStorage()
        with mock.patch.object(storage, 'manifest_storage') as manifest_storage_mock:
            manifest_storage_mock.exists.return_value = True
            storage.save_manifest()
        manifest_storage_mock.delete.assert_called_once_with('staticfiles.json')

    def test_add_unix_path_keys_to_paths(self):
        storage = StaticHashedCloudinaryStorage()
        paths = {
            'dir/1': 1,
            'dir\\2': 2
        }
        expected_paths = paths.copy()
        expected_paths['dir/2'] = 2
        storage.add_unix_path_keys_to_paths(paths)
        self.assertEqual(paths, expected_paths)
