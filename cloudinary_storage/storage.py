import os

import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.deconstruct import deconstructible
from django.conf import settings
from django.contrib.staticfiles.storage import HashedFilesMixin

from . import app_settings
from .helpers import get_resources_by_path

RESOURCE_TYPES = {
    'IMAGE': 'image',
    'RAW': 'raw',
    'VIDEO': 'video'
}


@deconstructible
class MediaCloudinaryStorage(Storage):
    RESOURCE_TYPE = RESOURCE_TYPES['IMAGE']
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
        return cloudinary.uploader.upload(content, **options)

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
    RESOURCE_TYPE = RESOURCE_TYPES['RAW']


class VideoMediaCloudinaryStorage(MediaCloudinaryStorage):
    RESOURCE_TYPE = RESOURCE_TYPES['VIDEO']


storages_per_type = {
    RESOURCE_TYPES['IMAGE']: MediaCloudinaryStorage(),
    RESOURCE_TYPES['RAW']: RawMediaCloudinaryStorage(),
    RESOURCE_TYPES['VIDEO']: VideoMediaCloudinaryStorage(),
}


class StaticCloudinaryStorage(MediaCloudinaryStorage):
    RESOURCE_TYPE = RESOURCE_TYPES['RAW']
    TAG = app_settings.STATIC_TAG

    def url(self, name):
        if settings.DEBUG:
            return settings.STATIC_URL + name
        return super().url(name)

    def _upload(self, name, content):
        return cloudinary.uploader.upload(content, public_id=name, resource_type=self.RESOURCE_TYPE,
                                          invalidate=True, tags=self.TAG)

    file_hash = HashedFilesMixin.file_hash  # we only need 1 method, so we do this instead of subclassing

    def _exists_with_etag(self, name, content):
        url = self._get_url(name)
        response = requests.head(url)
        if response.status_code == 404:
            return False
        etag = response.headers['ETAG'].split('"')[1]
        hash = self.file_hash(name, content)
        return etag.startswith(hash)

    def _save(self, name, content):
        if self._exists_with_etag(name, content):
            return name
        else:
            content.seek(0)
            return super()._save(name, content)


class ManifestCloudinaryStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        location = app_settings.STATICFILES_MANIFEST_ROOT
        super().__init__(location, base_url, *args, **kwargs)
