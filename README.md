# Django Cloudinary Storage

Django Cloudinary Storage is a Django package that facilitates integration with [Cloudinary](https://cloudinary.com/)
by implementing [Django Storage API](https://docs.djangoproject.com/en/stable/howto/custom-file-storage/).
With several lines of configuration, you can start using Cloudinary for both media and static files.
Also, it provides management commands for removing unnecessary files, so any cleanup will be a breeze.
It uses [pycloudinary](https://github.com/cloudinary/pycloudinary) package under the hood.

[![Tests](https://github.com/klis87/django-cloudinary-storage/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/klis87/django-cloudinary-storage/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/django-cloudinary-storage.svg)](https://pypi.org/project/django-cloudinary-storage/)
[![Django versions](https://img.shields.io/pypi/frameworkversions/django/django-cloudinary-storage.svg)](https://pypi.org/project/django-cloudinary-storage/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-cloudinary-storage.svg)](https://pypi.org/project/django-cloudinary-storage/)
[![License](https://img.shields.io/pypi/l/django-cloudinary-storage.svg)](https://github.com/klis87/django-cloudinary-storage/blob/master/LICENSE)

## Table of contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage with media files](#usage-with-media-files)
  - [Usage with raw files](#usage-with-raw-files)
  - [Usage with video files](#usage-with-video-files)
- [Usage with static files](#usage-with-static-files)
- [Management commands](#management-commands)
  - [deleteorphanedmedia](#deleteorphanedmedia)
  - [deleteredundantstatic](#deleteredundantstatic)
- [Settings](#settings)
- [Upgrading from 0.3](#upgrading-from-03)
- [How to run tests](#how-to-run-tests)

## Requirements

The package requires Python 3.10+ and Django 4.2+.

## Installation

To install the package, just run:

```
$ pip install django-cloudinary-storage
```

If you need to upload any video files, run:

```
$ pip install django-cloudinary-storage[video]
```

which will additionally install [python-magic](https://github.com/ahupp/python-magic) for uploaded video validation.

Also, in case you use Django `ImageField`, make sure you have Pillow installed:

```
$ pip install Pillow
```

Once you have done that, add `cloudinary` and `cloudinary_storage` to your installed apps in your `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    # ...
]
```

Next, you need to add Cloudinary credentials to `settings.py`:

```python
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'your_cloud_name',
    'API_KEY': 'your_api_key',
    'API_SECRET': 'your_api_secret'
}
```

Instead of putting credentials in `settings.py`, you can provide them as `CLOUDINARY_CLOUD_NAME`,
`CLOUDINARY_API_SECRET` and `CLOUDINARY_API_KEY` environment variables. It is possible as well to set only
`CLOUDINARY_URL` variable, combining all the information, for example:

```
$ export CLOUDINARY_URL=cloudinary://your_api_key:your_api_secret@your_cloud_name
```

For those of you who use Heroku, that's a very good news, because you won't need to set it yourself, as Heroku sets
`CLOUDINARY_URL` environment variable for you (provided you use Cloudinary as Heroku addon).

Also, be aware that `settings.py` takes precedence over environment variables.

## Usage with media files

The package provides three media storages:

- `cloudinary_storage.storage.MediaCloudinaryStorage` for images
- `cloudinary_storage.storage.RawMediaCloudinaryStorage` for raw files, like txt, pdf
- `cloudinary_storage.storage.VideoMediaCloudinaryStorage` for videos

Above distinction is necessary as Cloudinary API needs to know resource type in many of its methods.

Now, let's consider the most probable scenario that you will use Cloudinary for images uploaded by users of your
website. Let's say you created a following Django model:

```python
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='images/', blank=True)
```

All you need to do is to define `STORAGES` dictionary in `settings.py`:

```python
STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',  # or any media storage you'd like to use
    },
    'staticfiles': {
        # Django default storage for static files, see "Usage with static files" to keep them in Cloudinary
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
```

and add `MEDIA_URL` to your `settings.py` as well:

```python
MEDIA_URL = '/media/'  # or any prefix you choose
```

Please note that `STORAGES` replaces the whole default configuration, so you need to define both `default`
and `staticfiles` storages. Old `DEFAULT_FILE_STORAGE` setting doesn't work since Django 5.1.

And that's it! All your models with `ImageField` will be connected to Cloudinary.

Now, in order to put this image into your template, you can just type:

```django
<img src="{{ test_model_instance.image.url }}" alt="{{ test_model_instance.image.name }}">
```

However, doing that in this way, the image will be downloaded with its original size, as uploaded by a user.
To have more control, you can use Cloudinary image transformations. For example, to change the image's size,
use below code:

```django
{% load cloudinary %}
{% cloudinary test_model_instance.image.name width=100 height=100 %}
```

Of course, this only scratched the surface. Cloudinary is extremely powerful and I highly recommend you to check
[pycloudinary](https://github.com/cloudinary/pycloudinary) documentation.

Now, if you only need to use Cloudinary for images, you can skip the rest of this subsection.
However, if you are going to use it for videos and/or raw files, let's continue.

### Usage with raw files

If your users can upload text or other raw files, but not images, you would just use different default storage
in `settings.py`:

```python
STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.RawMediaCloudinaryStorage',
    },
    # ...
}
```

But what if they could upload both types? Well, not a problem! Just set the default file storage to the most
common resource type, and for fields of different type, you will need to set a correct storage individually, like this:

```python
from django.db import models

from cloudinary_storage.storage import RawMediaCloudinaryStorage

class TestModelWithRawFileAndImage(models.Model):
    name = models.CharField(max_length=100)
    raw_file = models.FileField(upload_to='raw/', blank=True, storage=RawMediaCloudinaryStorage())
    image = models.ImageField(upload_to='images/', blank=True)  # no need to set storage, field will use the default one
```

In above example we assumed the default file storage is `cloudinary_storage.storage.MediaCloudinaryStorage`,
that's why we set storage explicitly only for `raw_file`.

### Usage with video files

Usage with video files is analogous to raw files, but you will need to use `validate_video` validator for video fields
to validate user's uploaded videos. If not, Cloudinary will raise an error if a user tries to upload non-video file,
which will crash your website. Of course, you could use your own validator, but if you want to use built-in one,
do it like this:

```python
from django.db import models

from cloudinary_storage.storage import VideoMediaCloudinaryStorage
from cloudinary_storage.validators import validate_video

class TestModelWithVideoAndImage(models.Model):
    name = models.CharField(max_length=100)
    video = models.FileField(upload_to='videos/', blank=True, storage=VideoMediaCloudinaryStorage(),
                             validators=[validate_video])
    image = models.ImageField(upload_to='images/', blank=True)  # no need to set storage, field will use the default one
```

## Usage with static files

In order to move your static files to Cloudinary, update your `settings.py`:

```python
STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',  # or any other media storage
    },
    'staticfiles': {
        'BACKEND': 'cloudinary_storage.storage.StaticHashedCloudinaryStorage',
    },
}

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

CLOUDINARY_STORAGE = {
    # other settings, like credentials
    'STATICFILES_MANIFEST_ROOT': BASE_DIR / 'manifest',
}
```

After that, run Django `collectstatic` command:

```
$ python manage.py collectstatic
```

`StaticHashedCloudinaryStorage` works just like Django `ManifestStaticFilesStorage`: `collectstatic` gathers your
static files in `STATIC_ROOT` and adds hash of their content to their names, like `css/style.a1b2c3d4e5f6.css`.
Once it is done, the final files are uploaded to Cloudinary. Files which are already uploaded with the same content
are skipped, so only new and modified files are uploaded, which saves both time and bandwidth. That's why `STATIC_ROOT`
is required, but it doesn't need to exist when your website is running, it is used only by `collectstatic`.

Please note that only files with hashed name will be uploaded by default - this behavior can be changed with
`UPLOAD_UNHASHED_STATIC_FILES` setting:

```python
CLOUDINARY_STORAGE = {
    # other settings, like credentials
    'UPLOAD_UNHASHED_STATIC_FILES': True,
}
```

Use it only when you need static files under constant urls, for example in HTML emails. If you are not sure why it is
useful to add hash to file names, shortly speaking, it allows static files to be safely cached by Cloudinary CDN and
web browsers. Without it files' modification would become very problematic, because your website's users would use
their private older copies. Hashing prevents this issue as any file change will change its url as well, which would
force a browser to download a new version of a file.

Also, be aware that `collectstatic` will create `staticfiles.json` file in `STATICFILES_MANIFEST_ROOT` directory,
which shows mapping of unhashed file names to their hashed versions. Your website needs it to know the names
of hashed files, so it must be available wherever your website is running. If you run `collectstatic` during
deployment, on the server which runs your website, the file is already there and you don't need to do anything.
If you run `collectstatic` only locally, commit `staticfiles.json` to your version control system, so it gets
deployed together with your code.

Images and videos referenced in your CSS files, like `background-image: url('../images/bg.jpg')`, are replaced with
absolute Cloudinary urls during `collectstatic`. It is necessary, because CSS files are kept in Cloudinary
as raw resources, while images and videos are kept as image and video resources, so relative urls wouldn't work.

In order to use static files from Cloudinary, make sure you write your templates in below style:

```django
{% load static %}
<link rel="stylesheet" href="{% static 'css/style.css' %}">
<img src="{% static 'images/dummy-static-image.jpg' %}" alt="dummy static image">
```

If you would like to apply Cloudinary transformations for static images or videos, please use `cloudinary_static`
template tag as follows:

```django
{% load cloudinary_static %}
{% cloudinary_static 'images/dummy-static-image.jpg' width=50 height=50 %}
```

You can adjust `STATIC_IMAGES_EXTENSIONS` and `STATIC_VIDEOS_EXTENSIONS` to set rules which file extensions are treated
as image or video files. Files with different extensions will be uploaded as Cloudinary raw files and no transformations
could be applied for those files. Also, please note that `cloudinary_static` is just a thin wrapper around `cloudinary`
tag from [pycloudinary](https://github.com/cloudinary/pycloudinary) library, so please go to its documentation
to see what transformations are possible.

`collectstatic` uses Cloudinary Admin API to check which files are already uploaded. It needs only a few API calls,
but please note that Cloudinary limits the number of Admin API calls per hour.

Please note that you must set `DEBUG` to `False` to fetch static files from Cloudinary. With `DEBUG` equal to `True`,
Django `staticfiles` app will use your local files for easier and faster development (unless you use
`cloudinary_static` template tag).

## Management commands

The package provides two management commands:

- `deleteorphanedmedia`
- `deleteredundantstatic`

Static files are uploaded by Django `collectstatic` command, see [Usage with static files](#usage-with-static-files).
Both commands use Cloudinary Admin API, which limits the number of API calls per hour.

### deleteorphanedmedia

Deletes needless media files, which are not connected to any model. It is possible to provide paths to prevent deletion
of given files in `EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS` in `settings.py`, for example:

```python
CLOUDINARY_STORAGE = {
    # other settings
    'EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS': ('path/', 'second-path/')
}
```

Optional arguments:

- `--noinput` - non-interactive mode, the command won't ask you to do any confirmations

### deleteredundantstatic

Deletes needless static files, namely all files uploaded to Cloudinary, which are not present in the current
`staticfiles.json` manifest, so make sure it is up-to-date. Unhashed files are kept only when
`UPLOAD_UNHASHED_STATIC_FILES` setting is `True`. The command works only with `StaticHashedCloudinaryStorage`.

Optional arguments:

- `--noinput` - non-interactive mode, the command won't ask you to do any confirmations

## Settings

Below you can see all available settings with default values:

```python
import os

from django.conf import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': None,  # required
    'API_KEY': None,  # required
    'API_SECRET': None,  # required
    'SECURE': True,
    'MEDIA_TAG': 'media',
    'INVALID_VIDEO_ERROR_MESSAGE': 'Please upload a valid video file.',
    'EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS': (),
    'STATIC_TAG': 'static',
    'STATICFILES_MANIFEST_ROOT': os.path.join(BASE_DIR, 'manifest'),
    'UPLOAD_UNHASHED_STATIC_FILES': False,
    'STATIC_IMAGES_EXTENSIONS': ['jpg', 'jpe', 'jpeg', 'jpc', 'jp2', 'j2k', 'wdp', 'jxr',
                                 'hdp', 'png', 'gif', 'webp', 'bmp', 'tif', 'tiff', 'ico'],
    'STATIC_VIDEOS_EXTENSIONS': ['mp4', 'webm', 'flv', 'mov', 'ogv', '3gp', '3g2', 'wmv',
                                 'mpeg', 'flv', 'mkv', 'avi'],
    'MAGIC_FILE_PATH': 'magic',
    'PREFIX': settings.MEDIA_URL
}
```

`CLOUD_NAME`, `API_KEY` and `API_SECRET` are mandatory, unless you provide them as environment variables, as described
in [Installation](#installation). The rest could be overwritten if required, as described below:

- `SECURE` - whether your Cloudinary files should be served over HTTP or HTTPS, HTTPS is the default, set it to False
  to switch to HTTP
- `MEDIA_TAG` - name assigned to your all media files, it has to be different than `STATIC_TAG`, usually you don't
  need to worry about this setting, it is useful when you have several websites which use the same Cloudinary account, when
  you should set it unique to distinguish it from other websites
- `INVALID_VIDEO_ERROR_MESSAGE` - error message which will be displayed in user's form when one tries to upload non-video
  file in video field
- `EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS` - looked by `deleteorphanedmedia` command, you can provide here tuple of paths
  which will never be deleted
- `STATIC_TAG` - name assigned to your all static files, it has to be different than `MEDIA_TAG`, please see `MEDIA_TAG`
  setting to see when it is useful
- `STATICFILES_MANIFEST_ROOT` - path where `staticfiles.json` will be saved after `collectstatic` command, by default
  it is `manifest` directory next to the installed package, so please set it to a directory in your project
- `UPLOAD_UNHASHED_STATIC_FILES` - whether `collectstatic` should upload files without hash in their names
  along with hashed ones, `False` is the default
- `STATIC_IMAGES_EXTENSIONS` - list of file extensions with which static files will be treated as Cloudinary images
- `STATIC_VIDEOS_EXTENSIONS` - list of file extensions with which static files will be uploaded as Cloudinary videos
- `MAGIC_FILE_PATH`: applicable only for Windows, needed for python-magic library for movie validation, please see
  [python-magic](https://github.com/ahupp/python-magic#dependencies) for reference
- `PREFIX` - prefix to your all files uploaded by `MediaCloudinaryStorage`, default `MEDIA_URL`, it can be useful when
  you use `FileSystemStorage` as default and `MediaCloudinaryStorage` for some models fields

## Upgrading from 0.3

Version 0.4 supports Django 4.2+ and Python 3.10+. If you use Cloudinary for static files, please note that:

- `STORAGES` setting must be used instead of `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE`,
  the old ones are removed in Django 5.1
- `STATIC_ROOT` setting is required, as static files are collected there before they are uploaded to Cloudinary
- `StaticCloudinaryStorage` is removed, use `StaticHashedCloudinaryStorage`
- the package doesn't overwrite `collectstatic` command anymore, so the order of `cloudinary_storage`
  and `django.contrib.staticfiles` in `INSTALLED_APPS` doesn't matter
- `--upload-unhashed-files` argument of `collectstatic` and `--keep-unhashed-files` argument
  of `deleteredundantstatic` are replaced by `UPLOAD_UNHASHED_STATIC_FILES` setting
- `staticfiles.json` format is changed, it will be regenerated by `collectstatic`, the first `collectstatic` after
  the upgrade will upload all your static files again

See [CHANGELOG](CHANGELOG.md) for all changes.

## How to run tests

Tests upload files to Cloudinary, so you need Cloudinary account. Please use a separate account for tests, because
some tests delete files. Put its credentials into `.env` file in the project root:

```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

Then, install [uv](https://docs.astral.sh/uv/) and run:

```
$ uvx --with tox-uv tox
```

which will execute tests for all supported Python and Django versions. To run tests only for a given environment,
use `-e` argument, for example:

```
$ uvx --with tox-uv tox -e py312-dj52
```

Tests using Cloudinary are tagged with `cloudinary`. Cloudinary limits the number of API calls per hour, so if you
want to run tests often, you can skip them:

```
$ uvx --with tox-uv tox -- --exclude-tag cloudinary
```

There are also end-to-end tests, which run the test app on a real server and check it in a real browser
with [Playwright](https://playwright.dev/python/), covering both media and static files:

```
$ uv run --group e2e playwright install chromium  # only once
$ uv run --group e2e python tests/e2e/run_e2e.py
```

You can also play with the test app yourself, for example upload media files at `/uploads/` page:

```
$ mkdir -p /tmp/e2e/extra-static
$ export E2E_DIR=/tmp/e2e DJANGO_SETTINGS_MODULE=tests.e2e_settings
$ uv run --env-file .env python manage.py migrate
$ uv run --env-file .env python manage.py collectstatic --noinput
$ uv run --env-file .env python manage.py runserver
```

Files are uploaded to Cloudinary under `e2e-static` and `e2e-media` prefixes and tags.
