from django.contrib import admin

from .models import TestImageModel, TestVideoModel, TestModel, TestModelWithoutFile

admin.site.register(TestImageModel)
admin.site.register(TestVideoModel)
admin.site.register(TestModel)
admin.site.register(TestModelWithoutFile)
