Django Cloudinary Storage
=========================

Django Cloudinary Storage is a Django package that facilitates integration with [Cloudinary](http://cloudinary.com/)
by implementing [Django Storage API](https://docs.djangoproject.com/en/1.11/howto/custom-file-storage/).
With several lines of configuration, you can start using Cloudinary for both media and static files.
Also, it provides management commands for removing unnecessary files, so any cleanup will be a breeze.
It uses [pycloudinary](https://github.com/cloudinary/pycloudinary) package under the hood.

Table of content
-----------------

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage with media files](#usage-with-media-files)
    - [Usage with raw files](#usage-with-raw-files)
    - [Usage with video files](#usage-with-video-files)
- [Usage with static files](#usage-with-static-files)
- [Management commands](#management-commands)
    - [collectstatic](#collectstatic)
    - [deleteorphanedmedia](#deleteorphanedmedia)
    - [deleteredundantstatic](#deleteredundantstatic)
- [Settings](#settings)
- [How to run tests](#how-to-run-tests)

Requirements
------------

The package requires Python 2.7 or 3.4+ and Django 1.8+. It has been tested on Linux, Windows and Mac OS X.

Installation
------------

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

Once you have done that, add `cloudinary` and `cloudinary_storage` to you installed apps in your `settings.py`. If you
are going to use this package for static and/or media files, make sure that `cloudinary_storage` is before `django.contrib.staticfiles`:
```python
INSTALLED_APPS = [
    # ...
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    # ...
]
```
because django-cloudinary-storage overwrites Django `collectstatic` command. If you are going to use it only for media files
though, it is `django.contrib.staticfiles` which has to be first:
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

Usage with media files
----------------------

The package provides three media storages:
- `cloudinary_storage.storage.MediaCloudinaryStorage` for images
- `cloudinary_storage.storage.RawMediaCloudinaryStorage` for raw files, like txt, pdf
- `cloudinary_storage.storage.VideoMediaCloudinaryStorage` for videos

Above distinction if necessary as Cloudinary API needs to know resource type in many of its methods.

Now, let's consider the most probable scenario that you will use Cloudinary for images uploaded by users of your
website. Let's say you created a following Django model:
```python
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='images/', blank=True)
```
All you need to do is to add two lines to `settings.py`:
```python
MEDIA_URL = '/media/'  # or any prefix you choose
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```
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
Of cource, this only scratched the surface. Cloudinary is extremely powerful and I highly recommend you to check
[pycloudinary](https://github.com/cloudinary/pycloudinary) documentation.

Now, if you only need to use Cloudinary for images, you can skip the rest of this subsection.
However, if you are going to use it for videos and/or raw files, let's continue.

### Usage with raw files

If your users can upload text or other raw files, but not images, you would just use different default storage
in `settings.py`:
```python
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.RawMediaCloudinaryStorage'
```
But what if they could upload both types? Well, not a problem! Just set `DEFAULT_FILE_STORAGE` setting to the most
common resource type, and for fields of different type, you will need to set a correct storage individually, like this:
```python
from django.db import models

from cloudinary_storage.storage import RawMediaCloudinaryStorage

class TestModelWithRawFileAndImage(models.Model):
    name = models.CharField(max_length=100)
    raw_file = models.ImageField(upload_to='raw/', blank=True, storage=RawMediaCloudinaryStorage())
    image = models.ImageField(upload_to='images/', blank=True)  # no need to set storage, field will use the default one
```
In above example we assumed `DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'`,
that's why we set storage explicitly only for `raw_file`.

### Usage with video files

Usage with video files is analogous to raw files, but you will need to use `validate_video` validator for video fields
to validate user's uploaded videos. If not, Cloudinary will raise an error if a user tries to upload non-video file,
which will crash your website. Of cource, you could use your own validator, but if you want to use built-in one,
do it like this:
```python
from django.db import models

from cloudinary_storage.storage import VideoMediaCloudinaryStorage
from cloudinary_storage.validators import validate_video

class TestModelWithVideoAndImage(models.Model):
    name = models.CharField(max_length=100)
    video = models.ImageField(upload_to='videos/', blank=True, storage=VideoMediaCloudinaryStorage(),
                              validators=[validate_video])
    image = models.ImageField(upload_to='images/', blank=True)  # no need to set storage, field will use the default one
```

Usage with static files
-----------------------

In order to move your static files to Cloudinary, update your `settings.py`:
```python
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'cloudinary_storage.storage.StaticHashedCloudinaryStorage'
```

After that, run Django `collectstatic` command:
```
$ python manage.py collectstatic
```

Please note that only files with hashed name will be uploaded by default - this behavior can be changed by adding
`--upload-unhashed-files` argument to `collectstatic` command. If you are not sure why it is useful to add hash to file
names, shortly speaking, it allows static files to be safely cached by Cloudinary CDN and web browsers. Without it
files' modification would become very problematic, because your website's users would use their private older copies.
Hashing prevents this issue as any file change will change its url as well, which would force a browser to download
a new version of a file.

Also, be aware that `collectstatic` will create a JSON file, which shows mapping of unhashed file names to their hashed
versions. This file will be available at `./manifest/staticfiles.json` by default - you could change that
in your `settings.py`, for example:
```python
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLOUDINARY_STORAGE = {
    # other settings, like credentials
    'STATICFILES_MANIFEST_ROOT': os.path.join(BASE_DIR, 'my-manifest-directory')
}
```
It is highly recommended to keep up-to-date version of this file in your version control system.

In order to use static files from Cloudinary, make sure you write your templates in below style:
```django
{% load static from staticfiles %}
<link rel="stylesheet" href="{% static 'css/style.css' %}">
<img src="{% static 'images/dummy-static-image.jpg' %}" alt="dummy static image">
```
In Django 1.10 and later, you could use `{% load static %}` instead of `{% load static from staticfiles %}`.

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

Please note that you must set `DEBUG` to `False` to fetch static files from Cloudinary. With `DEBUG` equal to `True`,
Django `staticfiles` app will use your local files for easier and faster development (unless you use
`cloudinary_static` template tag).

Management commands
-------------------

The package provides three management commands:
- `collectstatic`
- `deleteorphanedmedia`
- `deleteredundantstatic`

### collectstatic

Adds minor modifications to Django `collectstatic` to improve upload performance. It uploads only hashed files
as the default. Also, it uploads a file only when necessary, namely it won't upload the file if a file with the same
name and content will be already uploaded to Cloudinary, which will save both time and bandwidth.

Optional arguments:
- `--upload-unhashed-files` - uploads files without hash added to their name along with hashed ones, use it only
when it is really necessary
- `--noinput` - non-interactive mode, the command won't ask you to do any confirmations

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

Deletes needless static files.

Optional arguments:
- `--keep-unhashed-files` - use it if you use `collectstatic` with `--upload-unhashed-files` argument,
without it this command will always delete all unhashed files
- `--noinput` - non-interactive mode, the command won't ask you to do any confirmations

Settings
--------

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
    'STATIC_IMAGES_EXTENSIONS': ['jpg', 'jpe', 'jpeg', 'jpc', 'jp2', 'j2k', 'wdp', 'jxr',
                                 'hdp', 'png', 'gif', 'webp', 'bmp', 'tif', 'tiff', 'ico'],
    'STATIC_VIDEOS_EXTENSIONS': ['mp4', 'webm', 'flv', 'mov', 'ogv' ,'3gp' ,'3g2' ,'wmv' ,
                                 'mpeg' ,'flv' ,'mkv' ,'avi'],
    'MAGIC_FILE_PATH': 'magic',
    'PREFIX': settings.MEDIA_URL
}
```
`CLOUD_NAME`, `API_KEY` and `API_SECRET` are mandatory and you need to define them in `CLOUDINARY_STORAGE` dictionary
in `settings.py`, the rest could be overwritten if required, as described below:
- `SECURE` - whether your Cloudinary files should be server over HTTP or HTTPS, HTTPS is the default, set it to False
to switch to HTTP
- `MEDIA_TAG` - name assigned to your all media files, it has to be different than `STATIC_TAG`, usually you don't
need to worry about this setting, it is useful when you have several websites which use the same Cloudinary acount, when
you should set it unique to distinguish it from other websites,
- `INVALID_VIDEO_ERROR_MESSAGE` - error message which will be desplayed in user's form when one tries to upload non-video
file in video field
- `EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS` - looked by `deleteorphanedmedia` command, you can provide here tuple of paths
which will never be deleted
- `STATIC_TAG` - name assigned to your all static files, it has to be different than `MEDIA_TAG`, please see `MEDIA_TAG`
setting to see when it is useful
- `STATICFILES_MANIFEST_ROOT` - path where `staticfiles.json` will be saved after `collectstatic` command, `./manifest`
is the default location
- `STATIC_IMAGES_EXTENSIONS` - list of file extensions with which static files will be treated as Cloudinary images
- `STATIC_VIDEOS_EXTENSIONS` - list of file extensions with which static files will be uploaded as Cloudinary videos
- `MAGIC_FILE_PATH`: applicable only for Windows, needed for python-magic library for movie validation, please see
[python-magic](https://github.com/ahupp/python-magic#dependencies) for reference
- `PREFIX` - prefix to your all files uploaded by `MediaCloudinaryStorage`, default `MEDIA_URL`, it can be useful when
you use `FileSystemStorage` as default and `MediaCloudinaryStorage` for some models fields

How to run tests
----------------

First, install tox:
```
$ pip install tox
```

After that, edit `tox.ini` file and input your Cloudinary credentials in `setenv`.

Then, just run:
```
$ tox
```
which will execute tests for Python 2.7, 3.4 - 3,5 and Django 1.8 - 1.11 (and additionally for Python 3.6 and Django 1.11).
At the end you will see coverage report in your console. HTML version of this report will be available in `./htmlcov/index.html`
file.

If you only need to run tests for your environment, add `-e` argument to `tox` command in
`{py27,py34,py35}-dj{18,19,110,111}` format (plus `py36-dj111`), for example:
```
$ tox -e py34-dj110
```
which will run tests for Python 3.4 and Django 1.10.
