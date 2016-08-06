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
        content = ContentFile(b'Content of file')
        file_model = TestModel(name='with file')
        file_model.file.save(get_random_name(), content)
        cls.file_name = file_model.file.name
        file_model = TestModel(name='with file')
        file_model.file.save(get_random_name(), content)
        cls.file_name_2 = file_model.file.name
        image = ImageFile(open('tests/dummy-image.jpg', 'rb'))
        image_model = TestImageModel(name='with image')
        image_model.file.save(get_random_name(), image)
        cls.file_name_3 = image_model.file.name

    def test_get_resource_types(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual({'raw', 'image'}, command.get_resource_types())

    def test_get_uploaded_media(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual(command.get_uploaded_media(), {self.file_name, self.file_name_2, self.file_name_3})

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        raw_storage = RawMediaCloudinaryStorage()
        raw_storage.delete(cls.file_name)
        raw_storage.delete(cls.file_name_2)
        image_storage = MediaCloudinaryStorage()
        image_storage.delete(cls.file_name_3)
