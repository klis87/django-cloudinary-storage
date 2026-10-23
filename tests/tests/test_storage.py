import errno
import os.path

from requests.exceptions import HTTPError
from django.test import tag, SimpleTestCase, override_settings
from django.core.files.base import ContentFile, File

from cloudinary_storage.storage import (MediaCloudinaryStorage, ManifestCloudinaryStorage,
                                        StaticHashedCloudinaryStorage, RESOURCE_TYPES)
from cloudinary_storage import app_settings
from tests.tests.test_helpers import (get_random_name, import_mock, TemporaryStaticRootTestsMixin,
                                      STYLE_MD5, IMAGE_MD5)

mock = import_mock()

TAG = get_random_name()


@tag('cloudinary')
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


class StaticHashedCloudinaryStorageHelpersTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    def setUp(self):
        self.storage = StaticHashedCloudinaryStorage(tag=get_random_name())
        self.storage.hashed_files = {'file.css': 'file.123.css', 'file.jpg': 'file.123.jpg'}

    @override_settings(DEBUG=True)
    def test_url_with_debug_true(self):
        self.assertEqual(self.storage.url('file.css'), '/static/file.css')

    def test_url_of_raw_file_with_debug_false(self):
        self.assertTrue(self.storage.url('file.css').endswith('/raw/upload/v1/static/file.123.css'))

    def test_url_of_image_file_with_debug_false(self):
        self.assertTrue(self.storage.url('file.jpg').endswith('/image/upload/v1/static/file.123.jpg'))

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

    def test_get_public_id_of_raw_file(self):
        self.assertEqual(self.storage._get_public_id('dir/file.css'), 'static/dir/file.css')

    def test_get_public_id_of_image_file_removes_extension(self):
        self.assertEqual(self.storage._get_public_id('dir/file.jpg'), 'static/dir/file')

    def test_get_public_id_of_windows_path(self):
        self.assertEqual(self.storage._get_public_id('dir\\file.css'), 'static/dir/file.css')

    @override_settings(STATIC_URL='/assets/v2/')
    def test_get_public_id_with_nested_static_url(self):
        self.assertEqual(self.storage._get_public_id('file.css'), 'assets/v2/file.css')


@mock.patch('cloudinary_storage.storage.cloudinary.uploader.upload')
@mock.patch('cloudinary_storage.storage.get_resources_md5_by_prefix', return_value={})
class StaticHashedCloudinaryStorageUploadTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    def setUp(self):
        self.storage = StaticHashedCloudinaryStorage(tag='static-tag')
        self.names = ['tests/css/style.css', 'tests/images/dummy-static-image.jpg']
        for name in self.names:
            with open(os.path.join('tests', 'static', name), 'rb') as f:
                self.storage.save(name, File(f))

    def tearDown(self):
        for name in self.names:
            self.storage.delete(name)

    def test_files_are_uploaded_with_proper_options(self, resources_mock, upload_mock):
        self.storage.upload_to_cloudinary(self.names)
        upload_mock.assert_has_calls([
            mock.call(self.storage.path('tests/css/style.css'), public_id='static/tests/css/style.css',
                      resource_type=RESOURCE_TYPES['RAW'], tags='static-tag', context={'md5': STYLE_MD5},
                      invalidate=False),
            mock.call(self.storage.path('tests/images/dummy-static-image.jpg'),
                      public_id='static/tests/images/dummy-static-image', resource_type=RESOURCE_TYPES['IMAGE'],
                      tags='static-tag', context={'md5': IMAGE_MD5}, invalidate=False),
        ], any_order=True)
        self.assertEqual(upload_mock.call_count, 2)

    def test_uploaded_files_are_listed_once_per_resource_type(self, resources_mock, upload_mock):
        self.storage.upload_to_cloudinary(self.names)
        resources_mock.assert_has_calls([
            mock.call(RESOURCE_TYPES['RAW'], 'static/'),
            mock.call(RESOURCE_TYPES['IMAGE'], 'static/'),
        ], any_order=True)
        self.assertEqual(resources_mock.call_count, 2)

    def test_files_with_the_same_content_are_not_uploaded(self, resources_mock, upload_mock):
        resources_mock.side_effect = lambda resource_type, prefix: {
            'static/tests/css/style.css': STYLE_MD5,
            'static/tests/images/dummy-static-image': IMAGE_MD5,
        }
        self.storage.upload_to_cloudinary(self.names)
        self.assertFalse(upload_mock.called)

    def test_files_with_different_content_are_uploaded_again_with_invalidation(self, resources_mock, upload_mock):
        resources_mock.side_effect = lambda resource_type, prefix: {
            'static/tests/css/style.css': 'different-md5',
            'static/tests/images/dummy-static-image': None,
        }
        self.storage.upload_to_cloudinary(self.names)
        self.assertEqual(upload_mock.call_count, 2)
        for call in upload_mock.call_args_list:
            self.assertTrue(call.kwargs['invalidate'])


class StaticHashedCloudinaryStorageTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    def test_manifest_is_kept_in_manifest_root(self):
        storage = StaticHashedCloudinaryStorage()
        self.assertIsInstance(storage.manifest_storage, ManifestCloudinaryStorage)
        self.assertEqual(storage.manifest_storage.location, os.path.abspath(app_settings.STATICFILES_MANIFEST_ROOT))

    def test_custom_manifest_storage_can_be_passed(self):
        manifest_storage = ManifestCloudinaryStorage(location='custom-manifest-dir')
        storage = StaticHashedCloudinaryStorage(manifest_storage=manifest_storage)
        self.assertIs(storage.manifest_storage, manifest_storage)

    def test_get_files_to_upload_returns_only_hashed_files(self):
        storage = StaticHashedCloudinaryStorage()
        storage.hashed_files = {'style.css': 'style.123.css'}
        self.assertEqual(storage.get_files_to_upload(), {'style.123.css'})

    def test_get_files_to_upload_with_unhashed_files(self):
        storage = StaticHashedCloudinaryStorage()
        storage.hashed_files = {'style.css': 'style.123.css'}
        with mock.patch.object(app_settings, 'UPLOAD_UNHASHED_STATIC_FILES', True):
            self.assertEqual(storage.get_files_to_upload(), {'style.css', 'style.123.css'})
