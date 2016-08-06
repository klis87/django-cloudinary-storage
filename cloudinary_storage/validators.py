import magic

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from cloudinary_storage import app_settings


def validate_video(value):
    mime = magic.from_buffer(value.file.read(1024), mime=True)
    value.file.seek(0)
    if not mime.startswith('video/'):
        raise ValidationError(_(app_settings.INVALID_VIDEO_ERROR_MESSAGE))
