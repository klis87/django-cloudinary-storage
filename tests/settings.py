SECRET_KEY = 'my-key'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'my-cloud-name',
    'API_KEY': 'my-api-key',
    'API_SECRET': 'my-api-secret'
}

INSTALLED_APPS = [
    'tests',
    'cloudinary_storage'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}
