import os

from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from tests.models import TestModel, TestVideoModel
from tests.tests.test_helpers import get_random_name
from cloudinary_storage.storage import RawMediaCloudinaryStorage, VideoMediaCloudinaryStorage
from cloudinary_storage import app_settings


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
        video = File(open(os.path.join('tests', 'dummy-files', 'dummy-video.mp4'), 'rb'))
        model = TestVideoModel(name='name')
        model.video.save(file_name, video)
        model.full_clean()
        file_name = model.video.name
        storage = VideoMediaCloudinaryStorage()
        try:
            self.assertTrue(storage.exists(file_name))
        finally:
            storage.delete(file_name)

    def test_invalid_video_raises_valuation_error(self):
        model = TestVideoModel(name='name')
        invalid_file = SimpleUploadedFile(get_random_name(), b'this is not a video', content_type='video/mp4')
        model.video = invalid_file
        with self.assertRaises(ValidationError) as e:
            model.full_clean()
        self.assertEqual(e.exception.messages, [app_settings.INVALID_VIDEO_ERROR_MESSAGE])
