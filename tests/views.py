from django import forms
from django.conf import settings
from django.shortcuts import render, redirect

from .models import TestImageModel, TestVideoModel


class TestImageModelForm(forms.ModelForm):
    class Meta:
        model = TestImageModel
        fields = ['name', 'file', 'image']


class TestVideoModelForm(forms.ModelForm):
    class Meta:
        model = TestVideoModel
        fields = ['name', 'video']


def index(request):
    return render(request, 'tests/index.html')


def uploads(request):
    image_form = TestImageModelForm(prefix='image')
    video_form = TestVideoModelForm(prefix='video')
    if request.method == 'POST':
        if 'image-name' in request.POST:
            image_form = TestImageModelForm(request.POST, request.FILES, prefix='image')
            form = image_form
        else:
            video_form = TestVideoModelForm(request.POST, request.FILES, prefix='video')
            form = video_form
        if form.is_valid():
            form.save()
            return redirect('uploads')
    return render(request, 'tests/uploads.html', {
        'image_form': image_form,
        'video_form': video_form,
        'image_models': TestImageModel.objects.order_by('pk'),
        'video_models': TestVideoModel.objects.order_by('pk'),
        'extra_stylesheet': getattr(settings, 'EXTRA_STYLESHEET', None),
    })
