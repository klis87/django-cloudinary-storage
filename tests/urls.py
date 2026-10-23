from django.contrib import admin
from django.conf import settings
from django.urls import path

from .views import index, uploads

urlpatterns = [
    path('', index, name='index'),
    path('uploads/', uploads, name='uploads'),
]

if 'django.contrib.admin' in settings.INSTALLED_APPS:
    urlpatterns.append(path('admin/', admin.site.urls))
