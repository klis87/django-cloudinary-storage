import os

import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from . import  app_settings
from .helpers import get_resources_by_path


@deconstructible
class MediaCloudinaryStorage(Storage):
    RESOURCE_TYPE = 'image'
    TAG = app_settings.MEDIA_TAG

    def __init__(self, tag=None, resource_type=None):
        if tag is not None:
            self.TAG = tag
        if resource_type is not None:
            self.RESOURCE_TYPE = resource_type

    def _open(self, name, mode='rb'):
        url = self._get_url(name)
        response = requests.get(url)
        if response.status_code == 404:
            raise IOError
        response.raise_for_status()
        file = ContentFile(response.content)
        file.name = name
        file.mode = mode
        return file

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

    def get_available_name(self, name, max_length=None):
        if max_length is None:
            return name
        else:
            return name[:max_length]

    def _normalize_path(self, path):
        if path != '' and not path.endswith('/'):
            path += '/'
        return path

    def listdir(self, path):
        path = self._normalize_path(path)
        resources = get_resources_by_path(self.RESOURCE_TYPE, self.TAG, path)
        directories = set()
        files = []
        for resource in resources:
            resource_tail = resource.replace(path, '', 1)
            if '/' in resource_tail:
                directory = resource_tail.split('/', 1)[0]
                directories.add(directory)
            else:
                files.append(resource_tail)
        return list(directories), files


class RawMediaCloudinaryStorage(MediaCloudinaryStorage):
    RESOURCE_TYPE = 'raw'
