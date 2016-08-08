from uuid import uuid4

from cloudinary_storage import app_settings
from cloudinary_storage.storage import MediaCloudinaryStorage


def get_random_name():
    return str(uuid4())


def set_media_tag(tag):
    MediaCloudinaryStorage.TAG = tag
    app_settings.MEDIA_TAG = tag
