from django.test import TestCase
from django.core.files.base import ContentFile

from tests.models import TestModel
from tests.test_helpers import get_random_name
from cloudinary_storage.storage import RawMediaCloudinaryStorage


class TestModelTests(TestCase):
    def test_file_exists_after_model_instance_with_file_is_saved(self):
        file_name = get_random_name()
        content = ContentFile(b'Content of model file')
        model = TestModel(name='name')
        model.file.save(file_name, content)
        file_name = model.file.name
        storage = RawMediaCloudinaryStorage()
        try:
            self.assertTrue(storage.exists(file_name))
        finally:
            storage.delete(file_name)
