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
        cls.file_name = cls.create_model_with_file(TestModel).file.name
        cls.file_name_2 = cls.create_model_with_file(TestModel).file.name
        image_model_instance = cls.create_model_with_file(TestImageModel)
        cls.file_name_3 = image_model_instance.file.name
        image = ImageFile(open('tests/dummy-image.jpg', 'rb'))
        image_model_instance.image.save(get_random_name(), image)
        cls.file_name_4 = image_model_instance.image.name

    @classmethod
    def create_model_with_file(cls, Model):
        content = ContentFile(b'Content of file')
        model_instance = Model(name='with file')
        model_instance.file.save(get_random_name(), content)
        return model_instance

    def test_get_resource_types(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual({'raw', 'image'}, command.get_resource_types())

    def test_get_uploaded_media(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual(command.get_uploaded_media(),
                         {self.file_name, self.file_name_2, self.file_name_3, self.file_name_4})

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        raw_storage = RawMediaCloudinaryStorage()
        raw_storage.delete(cls.file_name)
        raw_storage.delete(cls.file_name_2)
        raw_storage.delete(cls.file_name_3)
        image_storage = MediaCloudinaryStorage()
        image_storage.delete(cls.file_name_4)
