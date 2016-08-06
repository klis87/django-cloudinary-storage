from django.db import models

from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage, VideoMediaCloudinaryStorage
from cloudinary_storage.validators import validate_video


class TestModel(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='tests/', blank=True, storage=RawMediaCloudinaryStorage())


class TestImageModel(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='tests/', blank=True, storage=RawMediaCloudinaryStorage())
    image = models.ImageField(upload_to='tests-images/', blank=True, storage=MediaCloudinaryStorage())


class TestModelWithoutFile(models.Model):
    name = models.CharField(max_length=100)


class TestVideoModel(models.Model):
    name = models.CharField(max_length=100)
    video = models.FileField(upload_to='tests-videos/', blank=True, storage=VideoMediaCloudinaryStorage(),
                             validators=[validate_video])
