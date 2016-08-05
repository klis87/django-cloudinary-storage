from django.db import models

from cloudinary_storage.storage import RawMediaCloudinaryStorage


class TestModel(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='tests/', blank=True, storage=RawMediaCloudinaryStorage())
