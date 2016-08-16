Django Cloudinary Storage
=========================

Django Cloudinary Storage is a Django package that facilitates integration with [Cloudinary](http://cloudinary.com/)
by implementing [Django Storage Api](https://docs.djangoproject.com/en/1.10/howto/custom-file-storage/).
With several lines of configuration, you can start using Cloudinary for both media and static files.
Also, it provides management commands for removing unnecessary files, so any cleanup will be a breeze.
It uses [pycloudinary](https://github.com/cloudinary/pycloudinary) package under the hood.

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
which will install [python-magic](https://github.com/ahupp/python-magic) for uploaded video validation.

Also, in case you use Django `ImageField`, make sure you have Pillow installed:
```
$ pip install Pillow
```

Once you have done that, add cloudinary_storage to you installed apps in your `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    # ...
]
```
Make sure that `cloudinary_storage` is before `django.contrib.staticfiles`, otherwise the package won't work properly.

Next, you need to add Cloudinary credentials to `settings.py`:
```python
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'your_cloud_name',
    'API_KEY': 'your_api_key',
    'API_SECRET': 'your_api_secret'
}
```

Usage with media files
----------------------

The package provides three media storages:
- `cloudinary_storage.storage.MediaCloudinaryStorage` for images
- `cloudinary_storage.storage.RawMediaCloudinaryStorage` for raw files, like txt, pdf
- `cloudinary_storage.storage.VideoMediaCloudinaryStorage` for videos

Above distinction if necessary as Cloudinary API needs to know resource type in many of its methods.

Now, let's consider the most probable scenario that you will use Cloudinary for images uploaded by users of your website.
Let's say you created a following Django model:
```python
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='images/', blank=True)
```
All you need to do is to add 1 line to `settings.py`:
```python
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```
And that's it! All your models with `ImageField` will be connected to Cloudinary.

Now, in order to put this image into your template, you can just type:
```django
<img src="{{ test_model_instance.image.url }}" alt="test model instance image">
```

However, doing that in this way, the image will be downloaded with its original size, as uploaded by a user. To have more
control, you can use Cloudinary image transformations. For example, to change the image's size, use below code:
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
But what if they could upload both types? Well, not a problem! Just set `DEFAULT_FILE_STORAGE` setting to the most common
resource type, and for fields of different type, you will need to set a correct storage individually, like this:
```python
from django.db import models

from cloudinary_storage.storage import RawMediaCloudinaryStorage

class TestModelWithRawFileAndImage(models.Model):
    name = models.CharField(max_length=100)
    raw_file = models.ImageField(upload_to='raw/', blank=True, storage=RawMediaCloudinaryStorage())
    image = models.ImageField(upload_to='images/', blank=True)  # no need to set storage, field will use the default one
```
In above example we assumed `DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'`, that's why we set
storage explicitly only for `raw_file`.

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
    video = models.ImageField(upload_to='videos/', blank=True, storage=VideoMediaCloudinaryStorage())
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
names, shortly speaking, it allowes static files to be safely cached by Cloudinary CDN and web browsers. Without it
files' modification would become very problematic, because your website's users would use their private older copies.
Hashing prevents this issue as any file change will change its url as well, which would force a browser to download
a new version of a file.

Also, be aware that `collectstatic` will create a JSON file, which shows mapping of unhashed file names to their hashed
versions. This file will be available at `./manifest/staticfiles.json` directory by default - you could change that
in your `settings.py`, for example:
```python
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLOUDINARY_STORAGE {
    # other settings, like credentials
    'STATICFILES_MANIFEST_ROOT': os.path.join(BASE_DIR, 'my-manifest-directory')
}
```
It is highly recommended to keep up-to-date version of this file in your version control system.

In order to use static files from Cloudinary, make sure you write your templates in below style:
```django
{% load static from staticfiles %}
<link rel="stylesheet" href="{% static 'css/style.css' %}">
```
In Django 1.10 and later, you could use `{% load static %}` instead of `{% load static from staticfiles %}`.

Please note that you must set `DEBUG` to `False` to fetch static files from Cloudinary. With `DEBUG` equal to `True`,
Django `staticfiles` app will use your local files for easier and faster development.
