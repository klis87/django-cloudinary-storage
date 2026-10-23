import json
import os

import cloudinary.api
import cloudinary.uploader
import requests
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.test import TestCase, SimpleTestCase, override_settings
from django.core.management import CommandError

from cloudinary_storage.management.commands.deleteorphanedmedia import Command as DeleteOrphanedMediaCommand
from cloudinary_storage.management.commands.deleteredundantstatic import Command as DeleteRedundantStaticCommand
from cloudinary_storage.storage import (MediaCloudinaryStorage, RawMediaCloudinaryStorage, RESOURCE_TYPES,
                                        storages_per_type)
from cloudinary_storage import app_settings
from tests.models import TestModel, TestImageModel, TestModelWithoutFile
from tests.tests.test_helpers import (get_random_name, set_media_tag, execute_command, import_mock,
                                      TemporaryStaticRootTestsMixin, STATIC_STORAGES, STATIC_HASHED_STORAGES,
                                      STYLE_HASH, IMAGE_HASH, STYLE_MD5, IMAGE_MD5)

mock = import_mock()

DEFAULT_MEDIA_TAG = app_settings.MEDIA_TAG


class BaseOrphanedMediaCommandTestsMixin(object):
    @classmethod
    def setUpClass(cls):
        super(BaseOrphanedMediaCommandTestsMixin, cls).setUpClass()
        set_media_tag(get_random_name())
        TestModelWithoutFile.objects.create(name='without file')
        TestModel.objects.create(name='without file')
        TestImageModel.objects.create(name='without image')
        cls.file = cls.add_file_to_model(TestModel(name='with file')).file.name
        cls.file_2 = cls.add_file_to_model(TestModel(name='with file')).file.name
        image_model_instance = cls.add_file_to_model(TestImageModel(name='with file and image'))
        cls.file_removed = image_model_instance.file.name
        cls.add_file_to_model(image_model_instance)
        cls.file_removed_2 = image_model_instance.file.name
        cls.add_file_to_model(image_model_instance)
        cls.file_3 = image_model_instance.file.name
        image = ImageFile(open(os.path.join('tests', 'dummy-files', 'dummy-image.jpg'), 'rb'))
        image_model_instance.image.save(get_random_name(), image)
        cls.file_4 = image_model_instance.image.name

    @classmethod
    def add_file_to_model(cls, model_instance):
        content = ContentFile(b'Content of file')
        model_instance.file.save(get_random_name(), content)
        return model_instance

    @classmethod
    def tearDownClass(cls):
        super(BaseOrphanedMediaCommandTestsMixin, cls).tearDownClass()
        raw_storage = RawMediaCloudinaryStorage()
        raw_storage.delete(cls.file)
        raw_storage.delete(cls.file_2)
        raw_storage.delete(cls.file_3)
        raw_storage.delete(cls.file_removed)
        raw_storage.delete(cls.file_removed_2)
        image_storage = MediaCloudinaryStorage()
        image_storage.delete(cls.file_4)
        set_media_tag(DEFAULT_MEDIA_TAG)


class DeleteOrphanedMediaCommandHelpersTests(BaseOrphanedMediaCommandTestsMixin, TestCase):
    def test_get_resource_types(self):
        command = DeleteOrphanedMediaCommand()
        expected = {RESOURCE_TYPES['RAW'], RESOURCE_TYPES['IMAGE'], RESOURCE_TYPES['VIDEO']}
        self.assertEqual(expected, command.get_resource_types())

    def test_get_file_storage_for_image_resource_type(self):
        command = DeleteOrphanedMediaCommand()
        storage = command.get_file_storage(RESOURCE_TYPES['IMAGE'])
        self.assertEqual(storage, storages_per_type[RESOURCE_TYPES['IMAGE']])

    def test_get_uploaded_media(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual(command.get_needful_files(),
                         {self.file, self.file_2, self.file_3, self.file_4})

    def test_files_to_remove(self):
        command = DeleteOrphanedMediaCommand()
        expected = {
            RESOURCE_TYPES['RAW']: {self.file_removed, self.file_removed_2},
            RESOURCE_TYPES['IMAGE']: set(),
            RESOURCE_TYPES['VIDEO']: set()
        }
        self.assertEqual(command.get_files_to_remove(), expected)

    def test_files_to_remove_with_exclude_setting(self):
        app_settings.EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS = ('tests/',)
        command = DeleteOrphanedMediaCommand()
        expected = {
            RESOURCE_TYPES['RAW']: set(),
            RESOURCE_TYPES['IMAGE']: set(),
            RESOURCE_TYPES['VIDEO']: set()
        }
        self.assertEqual(command.get_files_to_remove(), expected)
        app_settings.EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS = ()


class DeleteOrphanedMediaCommandExecutionTests(BaseOrphanedMediaCommandTestsMixin, TestCase):
    def test_command_execution_correctly_removes_orphaned_files(self):
        output = execute_command('deleteorphanedmedia', '--noinput')
        self.assertIn('2 files have been deleted successfully.', output)
        storage = RawMediaCloudinaryStorage()
        self.assertTrue(storage.exists(self.file))
        self.assertTrue(storage.exists(self.file_2))
        self.assertTrue(storage.exists(self.file_3))
        self.assertFalse(storage.exists(self.file_removed))
        self.assertFalse(storage.exists(self.file_removed_2))

    def test_command_execution_without_existing_orphaned_files(self):
        with mock.patch.object(DeleteOrphanedMediaCommand,
                               'get_flattened_files_to_remove',
                               return_value=set()):
            output = execute_command('deleteorphanedmedia')
            self.assertIn('There is no file to delete.', output)


class DeleteOrphanedMediaCommandPromptTests(TestCase):
    def test_command_execution_with_prompt_as_yes(self):
        with mock.patch.object(DeleteOrphanedMediaCommand,
                               'get_flattened_files_to_remove',
                               return_value={'1', '2', '3'}):
            with mock.patch.object(DeleteOrphanedMediaCommand,
                                   'delete_orphaned_files'):
                with mock.patch('cloudinary_storage.management.commands.deleteorphanedmedia.input', return_value='yes'):
                    output = execute_command('deleteorphanedmedia')
                    self.assertIn('3 files have been deleted successfully.', output)

    def test_command_execution_with_prompt_as_no(self):
        with mock.patch.object(DeleteOrphanedMediaCommand,
                               'get_flattened_files_to_remove',
                               return_value={'1'}):
            with mock.patch('cloudinary_storage.management.commands.deleteorphanedmedia.input', return_value='no'):
                output = execute_command('deleteorphanedmedia')
                self.assertIn('As ordered, no file has been deleted.', output)


HASHED_STYLE_PUBLIC_ID = 'static/tests/css/style.{}.css'.format(STYLE_HASH)
HASHED_IMAGE_PUBLIC_ID = 'static/tests/images/dummy-static-image.{}'.format(IMAGE_HASH)  # removed jpg extension
UNHASHED_STYLE_PUBLIC_ID = 'static/tests/css/style.css'
UNHASHED_IMAGE_PUBLIC_ID = 'static/tests/images/dummy-static-image'  # removed jpg extension


def get_uploaded_public_ids(upload_mock):
    return {call.kwargs['public_id'] for call in upload_mock.call_args_list}


@override_settings(STORAGES=STATIC_STORAGES)
@mock.patch('cloudinary_storage.storage.get_resources_md5_by_prefix', return_value={})
@mock.patch('cloudinary_storage.storage.cloudinary.uploader.upload')
class CollectStaticCommandTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    def test_command_uploads_collected_files(self, upload_mock, resources_mock):
        output = execute_command('collectstatic', '--noinput')
        self.assertIn('2 static files copied', output)
        self.assertEqual(get_uploaded_public_ids(upload_mock), {UNHASHED_STYLE_PUBLIC_ID, UNHASHED_IMAGE_PUBLIC_ID})

    def test_command_doesnt_upload_anything_with_dry_run(self, upload_mock, resources_mock):
        execute_command('collectstatic', '--noinput', '--dry-run')
        self.assertFalse(resources_mock.called)
        self.assertFalse(upload_mock.called)


@override_settings(STORAGES=STATIC_HASHED_STORAGES)
@mock.patch('cloudinary_storage.storage.get_resources_md5_by_prefix', return_value={})
@mock.patch('cloudinary_storage.storage.cloudinary.uploader.upload')
class CollectStaticCommandWithHashedStorageTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    def test_command_uploads_only_final_hashed_files(self, upload_mock, resources_mock):
        execute_command('collectstatic', '--noinput', '--clear')
        self.assertEqual(upload_mock.call_count, 2)
        self.assertEqual(get_uploaded_public_ids(upload_mock), {HASHED_STYLE_PUBLIC_ID, HASHED_IMAGE_PUBLIC_ID})

    def test_command_uploads_unhashed_files_with_unhashed_files_setting(self, upload_mock, resources_mock):
        with mock.patch.object(app_settings, 'UPLOAD_UNHASHED_STATIC_FILES', True):
            execute_command('collectstatic', '--noinput', '--clear')
        self.assertEqual(get_uploaded_public_ids(upload_mock), {HASHED_STYLE_PUBLIC_ID, HASHED_IMAGE_PUBLIC_ID,
                                                                UNHASHED_STYLE_PUBLIC_ID, UNHASHED_IMAGE_PUBLIC_ID})

    def test_command_doesnt_upload_already_uploaded_files(self, upload_mock, resources_mock):
        resources_mock.side_effect = lambda resource_type, prefix: {
            HASHED_STYLE_PUBLIC_ID: STYLE_MD5,
            HASHED_IMAGE_PUBLIC_ID: IMAGE_MD5,
        }
        execute_command('collectstatic', '--noinput', '--clear')
        self.assertFalse(upload_mock.called)

    def test_command_doesnt_upload_anything_with_dry_run(self, upload_mock, resources_mock):
        execute_command('collectstatic', '--noinput', '--clear', '--dry-run')
        self.assertFalse(resources_mock.called)
        self.assertFalse(upload_mock.called)

    def test_command_saves_manifest_file(self, upload_mock, resources_mock):
        execute_command('collectstatic', '--noinput', '--clear')
        with open(os.path.join(self.manifest_root, 'staticfiles.json')) as f:
            manifest = json.load(f)
        self.assertEqual(manifest['paths'], {
            'tests/css/style.css': 'tests/css/style.{}.css'.format(STYLE_HASH),
            'tests/images/dummy-static-image.jpg': 'tests/images/dummy-static-image.{}.jpg'.format(IMAGE_HASH),
        })

    def test_command_doesnt_upload_anything_when_post_processing_fails(self, upload_mock, resources_mock):
        with mock.patch('django.contrib.staticfiles.storage.HashedFilesMixin._post_process',
                        side_effect=ValueError('post processing failed')):
            with self.assertRaises(ValueError):
                execute_command('collectstatic', '--noinput', '--clear')
        self.assertFalse(upload_mock.called)


@override_settings(STORAGES=STATIC_HASHED_STORAGES, STATIC_URL='/static-{}/'.format(get_random_name()))
class CollectStaticCommandWithHashedStorageIntegrationTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    """
    Uploads files to Cloudinary for real, under a random STATIC_URL to be isolated from other tests.
    """
    @classmethod
    def tearDownClass(cls):
        prefix = staticfiles_storage._get_prefix()
        for resource_type in (RESOURCE_TYPES['RAW'], RESOURCE_TYPES['IMAGE']):
            cloudinary.api.delete_resources_by_prefix(prefix, resource_type=resource_type, invalidate=True)
        super(CollectStaticCommandWithHashedStorageIntegrationTests, cls).tearDownClass()

    def test_files_are_available_right_after_collectstatic_and_not_uploaded_again(self):
        execute_command('collectstatic', '--noinput')
        for name in ('tests/css/style.css', 'tests/images/dummy-static-image.jpg'):
            url = staticfiles_storage.url(name)
            self.assertEqual(requests.head(url).status_code, 200, url)
        with mock.patch('cloudinary_storage.storage.cloudinary.uploader.upload',
                        wraps=cloudinary.uploader.upload) as upload_mock:
            execute_command('collectstatic', '--noinput')
        self.assertFalse(upload_mock.called)


@override_settings(STORAGES=STATIC_HASHED_STORAGES)
class DeleteRedundantStaticCommandTests(TemporaryStaticRootTestsMixin, SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super(DeleteRedundantStaticCommandTests, cls).setUpClass()
        with mock.patch('cloudinary_storage.storage.get_resources_md5_by_prefix', return_value={}):
            with mock.patch('cloudinary_storage.storage.cloudinary.uploader.upload'):
                execute_command('collectstatic', '--noinput')

    @mock.patch('cloudinary_storage.storage.StaticHashedCloudinaryStorage.read_manifest', return_value=None)
    def test_command_raises_error_when_manifest_doesnt_exist(self, read_manifest_mock):
        with self.assertRaises(CommandError):
            execute_command('deleteredundantstatic', '--noinput')

    @override_settings(STORAGES=STATIC_STORAGES)
    def test_command_raises_error_without_hashed_storage(self):
        with self.assertRaises(CommandError):
            execute_command('deleteredundantstatic', '--noinput')

    def test_get_resource_types(self):
        command = DeleteRedundantStaticCommand()
        expected = {RESOURCE_TYPES['RAW'], RESOURCE_TYPES['IMAGE'], RESOURCE_TYPES['VIDEO']}
        self.assertEqual(expected, command.get_resource_types())

    def test_get_exclude_paths_returns_empty_tuple(self):
        command = DeleteRedundantStaticCommand()
        self.assertEqual(command.get_exclude_paths(), ())

    def test_get_needful_files_with_upload_unhashed_static_files_setting(self):
        command = DeleteRedundantStaticCommand()
        with mock.patch.object(app_settings, 'UPLOAD_UNHASHED_STATIC_FILES', True):
            needful_files = command.get_needful_files()
        self.assertEqual(needful_files, {HASHED_STYLE_PUBLIC_ID, HASHED_IMAGE_PUBLIC_ID,
                                         UNHASHED_STYLE_PUBLIC_ID, UNHASHED_IMAGE_PUBLIC_ID})

    def test_get_needful_files_without_upload_unhashed_static_files_setting(self):
        command = DeleteRedundantStaticCommand()
        self.assertEqual(command.get_needful_files(), {HASHED_STYLE_PUBLIC_ID, HASHED_IMAGE_PUBLIC_ID})

    def test_command_doesnt_remove_anything_without_uploaded_files(self):
        DeleteRedundantStaticCommand.TAG = get_random_name()
        output = execute_command('deleteredundantstatic', '--noinput')
        try:
            self.assertIn('There is no file to delete.', output)
        finally:
            DeleteRedundantStaticCommand.TAG = app_settings.STATIC_TAG

    def test_command_doesnt_remove_anything_when_only_needful_file_is_uploaded(self):
        command = DeleteRedundantStaticCommand()
        uploaded_resources = [
            (RESOURCE_TYPES['RAW'], ['style.css']),
            (RESOURCE_TYPES['IMAGE'], []),
            (RESOURCE_TYPES['VIDEO'], [])
        ]
        needful_files = {'style.css'}
        with mock.patch.object(command, 'get_uploaded_resources', return_value=uploaded_resources):
            with mock.patch.object(command, 'get_needful_files', return_value=needful_files):
                files_to_remove = command.get_files_to_remove()
        expected_response = {
            RESOURCE_TYPES['RAW']: set(),
            RESOURCE_TYPES['IMAGE']: set(),
            RESOURCE_TYPES['VIDEO']: set()
        }
        self.assertEqual(files_to_remove, expected_response)

    def test_command_removes_not_needed_file(self):
        command = DeleteRedundantStaticCommand()
        uploaded_resources = [
            (RESOURCE_TYPES['RAW'], ['style1.css']),
            (RESOURCE_TYPES['IMAGE'], []),
            (RESOURCE_TYPES['VIDEO'], [])
        ]
        needful_files = {'style.css'}
        with mock.patch.object(command, 'get_uploaded_resources', return_value=uploaded_resources):
            with mock.patch.object(command, 'get_needful_files', return_value=needful_files):
                files_to_remove = command.get_files_to_remove()
        expected_response = {
            RESOURCE_TYPES['RAW']: {'style1.css'},
            RESOURCE_TYPES['IMAGE']: set(),
            RESOURCE_TYPES['VIDEO']: set()
        }
        self.assertEqual(files_to_remove, expected_response)

    @mock.patch('cloudinary_storage.management.commands.deleteredundantstatic.cloudinary.uploader.destroy')
    def test_files_are_deleted_from_cloudinary_with_their_resource_type(self, destroy_mock):
        command = DeleteRedundantStaticCommand()
        command.delete_orphaned_files({
            RESOURCE_TYPES['RAW']: {'static/style.css'},
            RESOURCE_TYPES['IMAGE']: {'static/image'},
            RESOURCE_TYPES['VIDEO']: set()
        })
        destroy_mock.assert_has_calls([
            mock.call('static/style.css', invalidate=True, resource_type=RESOURCE_TYPES['RAW']),
            mock.call('static/image', invalidate=True, resource_type=RESOURCE_TYPES['IMAGE']),
        ], any_order=True)
