from operator import itemgetter
import os
import sys

import cloudinary

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver
from django.test.signals import setting_changed
from django.utils.six.moves import reload_module

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
user_settings = getattr(settings, 'CLOUDINARY_STORAGE', {})


def set_credentials(user_settings):
    try:
        credentials = itemgetter('CLOUD_NAME', 'API_KEY', 'API_SECRET')(user_settings)
    except KeyError:
        if os.environ.get('CLOUDINARY_URL'):
            return
        if (os.environ.get('CLOUDINARY_CLOUD_NAME') and os.environ.get('CLOUDINARY_API_KEY') and
                os.environ.get('CLOUDINARY_API_SECRET')):
            return
        else:
            raise ImproperlyConfigured('In order to use cloudinary storage, you need to provide '
                                       'CLOUDINARY_STORAGE dictionary with CLOUD_NAME, API_SECRET '
                                       'and API_KEY in the settings or set CLOUDINARY_URL variable '
                                       '(or CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET '
                                       'variables).')
    else:
        cloudinary.config(
            cloud_name=credentials[0],
            api_key=credentials[1],
            api_secret=credentials[2]
        )

set_credentials(user_settings)

cloudinary.config(
    secure=user_settings.get('SECURE', True)
)

MEDIA_TAG = user_settings.get('MEDIA_TAG', 'media')
INVALID_VIDEO_ERROR_MESSAGE = user_settings.get('INVALID_VIDEO_ERROR_MESSAGE', 'Please upload a valid video file.')
EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS = user_settings.get('EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS', ())

STATIC_TAG = user_settings.get('STATIC_TAG', 'static')
STATICFILES_MANIFEST_ROOT = user_settings.get('STATICFILES_MANIFEST_ROOT', os.path.join(BASE_DIR, 'manifest'))

STATIC_IMAGES_EXTENSIONS = user_settings.get('STATIC_IMAGES_EXTENSIONS',
                                             [
                                                 'jpg',
                                                 'jpe',
                                                 'jpeg',
                                                 'jpc',
                                                 'jp2',
                                                 'j2k',
                                                 'wdp',
                                                 'jxr',
                                                 'hdp',
                                                 'png',
                                                 'gif',
                                                 'webp',
                                                 'bmp',
                                                 'tif',
                                                 'tiff',
                                                 'ico'
                                             ])

STATIC_VIDEOS_EXTENSIONS = user_settings.get('STATIC_VIDEOS_EXTENSIONS',
                                             [
                                                 'mp4',
                                                 'webm',
                                                 'flv',
                                                 'mov',
                                                 'ogv',
                                                 '3gp',
                                                 '3g2',
                                                 'wmv',
                                                 'mpeg',
                                                 'flv',
                                                 'mkv',
                                                 'avi'
                                             ])

# used only on Windows, see https://github.com/ahupp/python-magic#dependencies for your reference
MAGIC_FILE_PATH = user_settings.get('MAGIC_FILE_PATH', 'magic')

PREFIX = user_settings.get('PREFIX', settings.MEDIA_URL)


@receiver(setting_changed)
def reload_settings(*args, **kwargs):
    setting_name, value = kwargs['setting'], kwargs['value']
    if setting_name in ['CLOUDINARY_STORAGE', 'MEDIA_URL']:
        reload_module(sys.modules[__name__])
