import hashlib
import logging
import os

import cloudinary
import cloudinary.api
import cloudinary.uploader
import requests
from django.conf import settings
from django.contrib.staticfiles.storage import ManifestFilesMixin, StaticFilesStorage
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from django.utils.deconstruct import deconstructible

from . import app_settings
from .helpers import get_resources_by_path, get_resources_md5_by_prefix

logger = logging.getLogger(__name__)

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

    def _get_resource_type(self, name):
        """
        Implemented to allow different resource types per file name
        within one storage class.
        """
        return self.RESOURCE_TYPE

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
        options = {'use_filename': True, 'resource_type': self._get_resource_type(name), 'tags': self.TAG}
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        return cloudinary.uploader.upload(content, **options)

    def _save(self, name, content):
        name = self._normalise_name(name)
        name = self._prepend_prefix(name)
        content = UploadedFile(content, name)
        response = self._upload(name, content)
        return response['public_id']

    def delete(self, name):
        response = cloudinary.uploader.destroy(name, invalidate=True, resource_type=self._get_resource_type(name))
        return response['result'] == 'ok'

    def _get_url(self, name):
        name = self._prepend_prefix(name)
        cloudinary_resource = cloudinary.CloudinaryResource(name, default_resource_type=self._get_resource_type(name))
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

    def size(self, name):
        url = self._get_url(name)
        response = requests.head(url)
        if response.status_code == 200:
            return int(response.headers['content-length'])
        else:
            return None

    def get_available_name(self, name, max_length=None):
        if max_length is None:
            return name
        else:
            return name[:max_length]

    def _normalize_path(self, path):
        if path != '' and not path.endswith('/'):
            path += '/'
        return path

    def _get_prefix(self):
        return app_settings.PREFIX

    def _prepend_prefix(self, name):
        prefix = self._get_prefix().lstrip('/')
        prefix = self._normalize_path(prefix)
        if not name.startswith(prefix):
            name = prefix + name
        return name

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

    def _normalise_name(self, name):
        return name.replace('\\', '/')


class RawMediaCloudinaryStorage(MediaCloudinaryStorage):
    RESOURCE_TYPE = RESOURCE_TYPES['RAW']


class VideoMediaCloudinaryStorage(MediaCloudinaryStorage):
    RESOURCE_TYPE = RESOURCE_TYPES['VIDEO']


storages_per_type = {
    RESOURCE_TYPES['IMAGE']: MediaCloudinaryStorage(),
    RESOURCE_TYPES['RAW']: RawMediaCloudinaryStorage(),
    RESOURCE_TYPES['VIDEO']: VideoMediaCloudinaryStorage(),
}


class StaticCloudinaryStorage(StaticFilesStorage):
    """
    Base storage for staticfiles kept in Cloudinary.
    collectstatic gathers files in STATIC_ROOT as usual, then they are uploaded to Cloudinary
    in post_process, once the final set of files is known.
    Uploads only unhashed files, so it is highly unrecommended to use it directly,
    because static files are cached both by Cloudinary CDN and browsers
    and changing files could become problematic.
    """
    RESOURCE_TYPE = RESOURCE_TYPES['RAW']
    TAG = app_settings.STATIC_TAG

    def __init__(self, *args, tag=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tag is not None:
            self.TAG = tag

    def _get_resource_type(self, name):
        """
        Implemented as static files can be of different resource types.
        Because web developers are the people who control those files, we can distinguish them
        simply by looking at their extensions, we don't need any content based validation.
        """
        extension = self._get_file_extension(name)
        if extension is None:
            return self.RESOURCE_TYPE
        elif extension in app_settings.STATIC_IMAGES_EXTENSIONS:
            return RESOURCE_TYPES['IMAGE']
        elif extension in app_settings.STATIC_VIDEOS_EXTENSIONS:
            return RESOURCE_TYPES['VIDEO']
        else:
            return self.RESOURCE_TYPE

    @staticmethod
    def _get_file_extension(name):
        substrings = name.split('.')
        if len(substrings) == 1:  # no extensions
            return None
        else:
            return substrings[-1].lower()

    def _remove_extension_for_non_raw_file(self, name):
        """
        Implemented as image and video files' Cloudinary public id
        shouldn't contain file extensions, otherwise Cloudinary url
        would contain doubled extension - Cloudinary adds extension to url
        to allow file conversion to arbitrary file, like png to jpg.
        """
        file_resource_type = self._get_resource_type(name)
        if file_resource_type is None or file_resource_type == self.RESOURCE_TYPE:
            return name
        else:
            extension = self._get_file_extension(name)
            return name[:-len(extension) - 1]

    def _get_prefix(self):
        prefix = settings.STATIC_URL.lstrip('/')
        if prefix != '' and not prefix.endswith('/'):
            prefix += '/'
        return prefix

    def _prepend_prefix(self, name):
        name = name.replace('\\', '/')
        prefix = self._get_prefix()
        if not name.startswith(prefix):
            name = prefix + name
        return name

    def _get_public_id(self, name):
        return self._remove_extension_for_non_raw_file(self._prepend_prefix(name))

    def url(self, name):
        if settings.DEBUG:
            return super().url(name)
        name = self._prepend_prefix(name)
        cloudinary_resource = cloudinary.CloudinaryResource(name, default_resource_type=self._get_resource_type(name))
        return cloudinary_resource.url

    def stored_name(self, name):
        """
        Implemented to standardize interface
        for StaticCloudinaryStorage and StaticHashedCloudinaryStorage
        """
        return name

    def _get_md5(self, name):
        md5 = hashlib.md5()
        with self.open(name) as file:
            for chunk in file.chunks():
                md5.update(chunk)
        return md5.hexdigest()

    def upload_to_cloudinary(self, names):
        """
        Uploads files from STATIC_ROOT to Cloudinary, skipping the ones already uploaded with the same content.
        Uploaded files are found by listing them with Admin API, not by requesting their urls,
        because Cloudinary CDN would cache 404 responses for files which are uploaded afterwards.
        """
        names = sorted(set(names))
        resource_types = {self._get_resource_type(name) for name in names}
        uploaded = {resource_type: get_resources_md5_by_prefix(resource_type, self._get_prefix())
                    for resource_type in resource_types}
        uploaded_count = 0
        for name in names:
            resource_type = self._get_resource_type(name)
            public_id = self._get_public_id(name)
            md5 = self._get_md5(name)
            if uploaded[resource_type].get(public_id) == md5:
                continue
            cloudinary.uploader.upload(self.path(name), public_id=public_id, resource_type=resource_type,
                                       tags=self.TAG, context={'md5': md5},
                                       invalidate=public_id in uploaded[resource_type])
            uploaded_count += 1
            logger.info('Uploaded %s to Cloudinary.', name)
        logger.info('%s static files uploaded to Cloudinary, %s unmodified.',
                    uploaded_count, len(names) - uploaded_count)

    def post_process(self, paths, dry_run=False, **options):
        if not dry_run:
            self.upload_to_cloudinary(paths)
        yield from ()


class ManifestCloudinaryStorage(FileSystemStorage):
    """
    Storage for manifest file which will keep map of hashed paths.
    Subclasses FileSystemStorage, so the manifest file is kept locally.
    It is highly recommended to keep the manifest in your version control system,
    then you are guaranteed the manifest will be used in all production environment,
    including Heroku and AWS Elastic Beanstalk.
    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        location = app_settings.STATICFILES_MANIFEST_ROOT if location is None else location
        super(ManifestCloudinaryStorage, self).__init__(location, base_url, *args, **kwargs)


class StaticHashedCloudinaryStorage(ManifestFilesMixin, StaticCloudinaryStorage):
    """
    Django ManifestStaticFilesStorage, which uploads the final hashed files to Cloudinary.
    Unhashed files are uploaded too when UPLOAD_UNHASHED_STATIC_FILES setting is True.
    """
    def __init__(self, *args, manifest_storage=None, **kwargs):
        if manifest_storage is None:
            manifest_storage = ManifestCloudinaryStorage()
        super().__init__(*args, manifest_storage=manifest_storage, **kwargs)

    def get_files_to_upload(self):
        files = set(self.hashed_files.values())
        if app_settings.UPLOAD_UNHASHED_STATIC_FILES:
            files.update(self.hashed_files.keys())
        return files

    def post_process(self, paths, dry_run=False, **options):
        yield from super().post_process(paths, dry_run=dry_run, **options)
        if not dry_run:
            self.upload_to_cloudinary(self.get_files_to_upload())
