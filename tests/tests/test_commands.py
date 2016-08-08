from unittest import mock
import os

from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils.six import StringIO

from cloudinary_storage.management.commands.deleteorphanedmedia import Command as DeleteOrphanedMediaCommand
from cloudinary_storage.storage import (MediaCloudinaryStorage, RawMediaCloudinaryStorage, StaticCloudinaryStorage,
                                        StaticHashedCloudinaryStorage, RESOURCE_TYPES)
from cloudinary_storage import app_settings
from tests.models import TestModel, TestImageModel, TestModelWithoutFile
from tests.tests.test_helpers import get_random_name, set_media_tag

DEFAULT_MEDIA_TAG = app_settings.MEDIA_TAG


def execute_command(*args):
    out = StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


class BaseOrphanedMediaCommandTestsMixin(object):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        image = ImageFile(open('tests/dummy-files/dummy-image.jpg', 'rb'))
        image_model_instance.image.save(get_random_name(), image)
        cls.file_4 = image_model_instance.image.name

    @classmethod
    def add_file_to_model(cls, model_instance):
        content = ContentFile(b'Content of file')
        model_instance.file.save(get_random_name(), content)
        return model_instance

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
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

    def test_get_uploaded_media(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual(command.get_uploaded_media(),
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
                with mock.patch('builtins.input', return_value='yes'):
                    output = execute_command('deleteorphanedmedia')
                    self.assertIn('3 files have been deleted successfully.', output)

    def test_command_execution_with_prompt_as_no(self):
        with mock.patch.object(DeleteOrphanedMediaCommand,
                               'get_flattened_files_to_remove',
                               return_value={'1'}):
            with mock.patch('builtins.input', return_value='no'):
                output = execute_command('deleteorphanedmedia')
                self.assertIn('As ordered, no file has been deleted.', output)


STATIC_FILES = ('tests/css/style.css', 'tests/css/font.css')


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
    def test_command_saves_hashed_static_files(self, save_mock):
        output = execute_command('collectstatic', '--noinput')
        self.assertEqual(save_mock.call_count, 2)
        for file in STATIC_FILES:
            self.assertIn(file, output)
        self.assertIn('0 static files copied, 2 post-processed.', output)

    def test_command_saves_unhashed_static_files_with_upload_unhashed_files_arg(self, save_mock):
        output = execute_command('collectstatic', '--noinput', '--upload-unhashed-files')
        self.assertEqual(save_mock.call_count, 4)
        for file in STATIC_FILES:
            self.assertIn(file, output)
        self.assertIn('2 static files copied, 2 post-processed.', output)

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
