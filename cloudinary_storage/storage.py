import os

import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from . import app_settings


@deconstructible
class MediaCloudinaryStorage(Storage):
    RESOURCE_TYPE = 'image'
    TAG = 'media'

    def __init__(self, tag=None, resource_type=None):
        if tag is not None:
            self.TAG = tag
        if resource_type is not None:
            self.RESOURCE_TYPE = resource_type

    def _upload(self, name, content):
        options = {'use_filename': True, 'resource_type': self.RESOURCE_TYPE, 'tags': self.TAG}
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        response = cloudinary.uploader.upload(content, **options)
        return response

    def _save(self, name, content):
        content = UploadedFile(content, name)
        response = self._upload(name, content)
        return response['public_id']

    def delete(self, name):
        response = cloudinary.uploader.destroy(name, invalidate=True, resource_type=self.RESOURCE_TYPE)
        return response['result'] == 'ok'

    def _get_url(self, name):
        cloudinary_resource = cloudinary.CloudinaryResource(name, default_resource_type=self.RESOURCE_TYPE)
        return cloudinary_resource.url

    def url(self, name):
        return self._get_url(name)

    def exists(self, name):
        url = self._get_url(name)
        response = requests.head(url)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True
