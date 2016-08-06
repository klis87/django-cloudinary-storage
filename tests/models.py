from django.db import models

from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage


class TestModel(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='tests/', blank=True, storage=RawMediaCloudinaryStorage())


class TestImageModel(models.Model):
    name = models.CharField(max_length=100)
    file = models.ImageField(upload_to='tests-images/', blank=True, storage=MediaCloudinaryStorage())
