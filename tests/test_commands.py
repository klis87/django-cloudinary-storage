from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile

from cloudinary_storage.management.commands.deleteorphanedmedia import Command as DeleteOrphanedMediaCommand
from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage
from tests.models import TestModel, TestImageModel, TestModelWithoutFile
from tests.test_helpers import get_random_name


class DeleteOrphanedMediaCommandTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        image = ImageFile(open('tests/dummy-image.jpg', 'rb'))
        image_model_instance.image.save(get_random_name(), image)
        cls.file_4 = image_model_instance.image.name

    @classmethod
    def add_file_to_model(cls, model_instance):
        content = ContentFile(b'Content of file')
        model_instance.file.save(get_random_name(), content)
        return model_instance

    def test_get_resource_types(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual({'raw', 'image'}, command.get_resource_types())

    def test_get_uploaded_media(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual(command.get_uploaded_media(),
                         {self.file, self.file_2, self.file_3, self.file_4})

    def test_files_to_remove(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual(command.get_files_to_remove(),
                         {'raw': {self.file_removed, self.file_removed_2}, 'image': set()})

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
