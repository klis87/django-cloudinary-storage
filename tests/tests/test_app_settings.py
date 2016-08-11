from django.utils.six.moves import reload_module as reload

from django.test import SimpleTestCase
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from cloudinary_storage import app_settings


class AppSettingsTests(SimpleTestCase):
    def assert_incomplete_settings_raise_error(self, property):
        default_settings = settings.CLOUDINARY_STORAGE.copy()
        del default_settings[property]
        with self.settings(CLOUDINARY_STORAGE=default_settings):
            with self.assertRaises(ImproperlyConfigured):
                reload(app_settings)

    def test_missing_CLOUD_NAME_setting_raises_error(self):
        self.assert_incomplete_settings_raise_error('CLOUD_NAME')

    def test_missing_API_SECRET_setting_raises_error(self):
        self.assert_incomplete_settings_raise_error('API_SECRET')

    def test_missing_API_KEY_setting_raises_error(self):
        self.assert_incomplete_settings_raise_error('API_KEY')

    def test_proper_configuration_doesnt_raise_error(self):
        reload(app_settings)
