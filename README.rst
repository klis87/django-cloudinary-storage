Django Cloudinary Storage
=========================
Django Cloudinary Storage is a Django package that facilitates integration with `Cloudinary <http://cloudinary.com/>`_
by implementing `Django Storage Api <https://docs.djangoproject.com/en/1.10/howto/custom-file-storage/>`_.
With several lines of configuration, you can start using Cloudinary for both media and static files.
Also, it provides management commands for removing unnecessary files, so any cleanup will be a breaze.
It uses `pycloudinary <https://github.com/cloudinary/pycloudinary>`_ package under the hood.

Requirements
------------
The package requires Python 2.7 or 3.4+ and Django 1.8+. It has been tested on Linux, Windows and Mac OS X.

Installation
------------
To install the package, just run:
::

  pip install django-cloudinary-storage
  
If you need to upload any video files, run:
::

  pip install django-cloudinary-storage[video]
which will install `python-magic <https://github.com/ahupp/python-magic>`_ for uploaded video validation.
