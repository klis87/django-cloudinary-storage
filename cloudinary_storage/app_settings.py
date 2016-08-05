from operator import itemgetter

import cloudinary

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

user_settings = getattr(settings, 'CLOUDINARY_STORAGE', {})

try:
    itemgetter('CLOUD_NAME', 'API_KEY', 'API_SECRET')(user_settings)
except KeyError:
    raise ImproperlyConfigured('In order to use cloudinary storage, you need to provide CLOUDINARY_STORAGE '
                               'dictionary with CLOUD_NAME, API_SECRET and API_KEY in the settings.')

cloudinary.config(
    cloud_name=user_settings.get('CLOUD_NAME'),
    api_key=user_settings.get('API_KEY'),
    api_secret=user_settings.get('API_SECRET'),
    secure=user_settings.get('SECURE', True)
)

MEDIA_TAG = user_settings.get('MEDIA_TAG', 'media')
