from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files import File

from tests.models import TestModel, TestVideoModel
from tests.test_helpers import get_random_name
from cloudinary_storage.storage import RawMediaCloudinaryStorage, VideoMediaCloudinaryStorage


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


class TestVideoModelTests(TestCase):
    def test_video_can_be_uploaded(self):
        file_name = get_random_name()
        video = File(open('tests/dummy-video.mp4', 'rb'))
        model = TestVideoModel(name='name')
        model.video.save(file_name, video)
        file_name = model.video.name
        storage = VideoMediaCloudinaryStorage()
        try:
            self.assertTrue(storage.exists(file_name))
        finally:
            storage.delete(file_name)
