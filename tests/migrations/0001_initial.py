# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-05 12:20
from __future__ import unicode_literals

import cloudinary_storage.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('file', models.FileField(blank=True, storage=cloudinary_storage.storage.RawMediaCloudinaryStorage(), upload_to='tests/')),
            ],
        ),
    ]
