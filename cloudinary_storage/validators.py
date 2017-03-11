import os

import magic

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from cloudinary_storage import app_settings


def validate_video(value):
    if os.name == 'nt':
        magic_object = magic.Magic(magic_file='magic', mime=True)
        mime = magic_object.from_buffer(value.file.read(1024))
    else:
        mime = magic.from_buffer(value.file.read(1024), mime=True)
    value.file.seek(0)
    if not mime.startswith('video/'):
        raise ValidationError(_(app_settings.INVALID_VIDEO_ERROR_MESSAGE))
