import os

from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.test import TestCase, SimpleTestCase, override_settings
from django.core.management import CommandError

from cloudinary_storage.management.commands.deleteorphanedmedia import Command as DeleteOrphanedMediaCommand
from cloudinary_storage.management.commands.deleteredundantstatic import Command as DeleteRedundantStaticCommand
from cloudinary_storage.storage import (MediaCloudinaryStorage, RawMediaCloudinaryStorage, StaticCloudinaryStorage,
                                        StaticHashedCloudinaryStorage, RESOURCE_TYPES, storages_per_type)
from cloudinary_storage import app_settings
from tests.models import TestModel, TestImageModel, TestModelWithoutFile
from tests.tests.test_helpers import (get_random_name, set_media_tag, execute_command, StaticHashedStorageTestsMixin,
                                      get_save_calls_counter_in_postprocess_of_adjustable_file,
                                      get_postprocess_counter_of_adjustable_file, import_mock)

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


STATIC_FILES = (
    os.path.join('tests', 'css', 'style.css'),
    os.path.join('tests', 'images', 'dummy-static-image.jpg')
)


@override_settings(STATICFILES_STORAGE='cloudinary_storage.storage.StaticCloudinaryStorage')
class CollectStaticCommandTests(SimpleTestCase):
    @mock.patch.object(StaticCloudinaryStorage, 'save')
    def test_command_saves_static_files(self, save_mock):
        output = execute_command('collectstatic', '--noinput')
        self.assertEqual(save_mock.call_count, 2)
        for file in STATIC_FILES:
            self.assertIn(file, output)
        self.assertIn('2 static files copied.', output)


@override_settings(STATICFILES_STORAGE='cloudinary_storage.storage.StaticHashedCloudinaryStorage')
@mock.patch.object(StaticHashedCloudinaryStorage, '_save')
class CollectStaticCommandWithHashedStorageTests(SimpleTestCase):
    @mock.patch.object(StaticHashedCloudinaryStorage, 'save_manifest')
    def test_command_saves_hashed_static_files(self, save_manifest_mock, save_mock):
        output = execute_command('collectstatic', '--noinput')
        self.assertEqual(save_mock.call_count, 1 * get_save_calls_counter_in_postprocess_of_adjustable_file() + 1)
        for file in STATIC_FILES:
            self.assertIn(file, output)
        post_process_counter = 1 + 1 * get_postprocess_counter_of_adjustable_file()
        self.assertIn('0 static files copied, {} post-processed.'.format(post_process_counter), output)

    @mock.patch.object(StaticHashedCloudinaryStorage, 'save_manifest')
    def test_command_saves_unhashed_static_files_with_upload_unhashed_files_arg(self, save_manifest_mock, save_mock):
        output = execute_command('collectstatic', '--noinput', '--upload-unhashed-files')
        self.assertEqual(save_mock.call_count, 2 + 1 + 1 * get_save_calls_counter_in_postprocess_of_adjustable_file())
        for file in STATIC_FILES:
            self.assertIn(file, output)
        post_process_counter = 1 + 1 * get_postprocess_counter_of_adjustable_file()
        self.assertIn('2 static files copied, {} post-processed.'.format(post_process_counter), output)

    def test_command_saves_manifest_file(self, save_mock):
        name = get_random_name()
        StaticHashedCloudinaryStorage.manifest_name = name
        execute_command('collectstatic', '--noinput')
        try:
            manifest_path = os.path.join(app_settings.STATICFILES_MANIFEST_ROOT, name)
            self.assertTrue(os.path.exists(manifest_path))
            os.remove(manifest_path)
        finally:
            StaticHashedCloudinaryStorage.manifest_name = 'staticfiles.json'


@override_settings(STATICFILES_STORAGE='cloudinary_storage.storage.StaticHashedCloudinaryStorage')
class DeleteRedundantStaticCommandTests(StaticHashedStorageTestsMixin, SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super(DeleteRedundantStaticCommandTests, cls).setUpClass()
        with mock.patch.object(StaticHashedCloudinaryStorage, '_upload'):
            execute_command('collectstatic', '--noinput')

    @mock.patch.object(StaticHashedCloudinaryStorage, 'read_manifest', return_value=None)
    def test_command_raises_error_when_manifest_doesnt_exist(self, read_manifest_mock):
        with self.assertRaises(CommandError):
            execute_command('deleteredundantstatic', '--noinput')

    def test_get_file_storage(self):
        command = DeleteRedundantStaticCommand()
        storage = command.get_file_storage(RESOURCE_TYPES['IMAGE'])
        self.assertEqual(storage, command.storage)

    def test_get_resource_types(self):
        command = DeleteRedundantStaticCommand()
        expected = {RESOURCE_TYPES['RAW'], RESOURCE_TYPES['IMAGE'], RESOURCE_TYPES['VIDEO']}
        self.assertEqual(expected, command.get_resource_types())

    def test_get_exclude_paths_returns_empty_tuple(self):
        command = DeleteRedundantStaticCommand()
        self.assertEqual(command.get_exclude_paths(), ())

    def test_get_needful_files_with_keep_unhashed_files_true(self):
        command = DeleteRedundantStaticCommand()
        command.keep_unhashed_files = True
        expected_response = {
            'static/tests/css/style.css',
            'static/tests/css/style.{}.css'.format(self.style_hash),
            'static/tests/images/dummy-static-image',  # removed jpg extension
            'static/tests/images/dummy-static-image.{}'.format(self.image_hash)  # removed jpg extension
        }
        self.assertEqual(command.get_needful_files(), expected_response)

    def test_get_needful_files_with_keep_unhashed_files_false(self):
        command = DeleteRedundantStaticCommand()
        command.keep_unhashed_files = False
        expected_response = {
            'static/tests/css/style.{}.css'.format(self.style_hash),
            'static/tests/images/dummy-static-image.{}'.format(self.image_hash)  # removed jpg extension
        }
        self.assertEqual(command.get_needful_files(), expected_response)

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
