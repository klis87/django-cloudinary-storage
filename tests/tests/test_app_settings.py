import os

from django.test import SimpleTestCase
from django.core.exceptions import ImproperlyConfigured

from cloudinary_storage.app_settings import set_credentials
from .test_helpers import import_mock

mock = import_mock()


@mock.patch.dict(os.environ, {}, clear=True)
class SetCredentialsWithoutEnvVariablesTests(SimpleTestCase):
    def assert_incomplete_settings_raise_error(self, settings):
        with self.assertRaises(ImproperlyConfigured):
            set_credentials(settings)

    def test_missing_CLOUD_NAME_setting_raises_error(self):
        self.assert_incomplete_settings_raise_error({'API_SECRET': 'secret', 'API_KEY': 'key'})

    def test_missing_API_SECRET_setting_raises_error(self):
        self.assert_incomplete_settings_raise_error({'CLOUD_NAME': 'name', 'API_KEY': 'key'})

    def test_missing_API_KEY_setting_raises_error(self):
        self.assert_incomplete_settings_raise_error({'CLOUD_NAME': 'name', 'API_SECRET': 'secret'})

    @mock.patch('cloudinary_storage.app_settings.cloudinary.config')
    def test_proper_configuration_correctly_sets_credentials(self, config_mock):
        set_credentials({'CLOUD_NAME': 'name', 'API_SECRET': 'secret', 'API_KEY': 'key'})
        config_mock.assert_called_once_with(cloud_name='name', api_secret='secret', api_key='key')



class SetCredentialsWithEnvVariablesTests(SimpleTestCase):
    def assert_incomplete_settings_raise_error(self, settings={}):
        with self.assertRaises(ImproperlyConfigured):
            set_credentials(settings)

    @mock.patch.dict(os.environ, {'CLOUDINARY_API_SECRET': 'secret', 'CLOUDINARY_API_KEY': 'key'}, clear=True)
    def test_missing_CLOUD_NAME_variable_raises_error(self):
        self.assert_incomplete_settings_raise_error()

    @mock.patch.dict(os.environ, {'CLOUDINARY_CLOUD_NAME': 'name', 'CLOUDINARY_API_KEY': 'key'}, clear=True)
    def test_missing_API_SECRET_variable_raises_error(self):
        self.assert_incomplete_settings_raise_error()

    @mock.patch.dict(os.environ, {'CLOUDINARY_CLOUD_NAME': 'name', 'CLOUDINARY_API_SECRET': 'secret'}, clear=True)
    def test_missing_API_KEY_variable_raises_error(self):
        self.assert_incomplete_settings_raise_error()

    @mock.patch('cloudinary_storage.app_settings.cloudinary.config')
    @mock.patch.dict(os.environ,
                     {
                         'CLOUDINARY_CLOUD_NAME': 'name',
                         'CLOUDINARY_API_SECRET': 'secret',
                         'CLOUDINARY_API_KEY': 'key'
                     },
                     clear=True)
    def test_complete_set_of_env_variables_doesnt_raise_error(self, config_mock):
        set_credentials({})
        self.assertFalse(config_mock.called)

    @mock.patch.dict(os.environ, {'CLOUDINARY_URL': 'my-url'}, clear=True)
    @mock.patch('cloudinary_storage.app_settings.cloudinary.config')
    def test_CLOUDINARY_URL_env_variable_doesnt_raise_error(self, config_mock):
        set_credentials({})
        self.assertFalse(config_mock.called)
