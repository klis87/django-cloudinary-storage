"""
Settings for end-to-end testing of the test app with a real server, browser and Cloudinary account.
All files are uploaded under e2e prefixes and tags, local files are kept in E2E_DIR.
"""
import os

from .settings import *  # noqa: F401,F403
from .settings import CLOUDINARY_STORAGE, INSTALLED_APPS, LOGGING

E2E_DIR = os.environ['E2E_DIR']

DEBUG = os.getenv('E2E_DEBUG') == '1'

INSTALLED_APPS = INSTALLED_APPS + ['cloudinary']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(E2E_DIR, 'db.sqlite3'),
    }
}

STATIC_URL = '/e2e-static/'
STATIC_ROOT = os.path.join(E2E_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(E2E_DIR, 'extra-static')]
EXTRA_STYLESHEET = os.getenv('E2E_EXTRA_STYLESHEET')

MEDIA_URL = '/e2e-media/'

CLOUDINARY_STORAGE = dict(
    CLOUDINARY_STORAGE,
    MEDIA_TAG='e2e-media',
    STATIC_TAG='e2e-static',
    STATICFILES_MANIFEST_ROOT=os.path.join(E2E_DIR, 'manifest'),
    UPLOAD_UNHASHED_STATIC_FILES=os.getenv('E2E_UNHASHED') == '1',
)

LOGGING = dict(LOGGING, loggers=dict(LOGGING['loggers'], cloudinary_storage={'handlers': ['console'], 'level': 'INFO'}))
