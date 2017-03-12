from django import template
from django.utils.safestring import mark_safe
from django.contrib.staticfiles.storage import staticfiles_storage

from cloudinary import CloudinaryResource

register = template.Library()

@register.simple_tag(name='cloudinary_static', takes_context=True)
def cloudinary_static(context, image, options_dict={}, **options):
    options = dict(options_dict, **options)
    try:
        if context['request'].is_secure() and 'secure' not in options:
            options['secure'] = True
    except KeyError:
        pass
    if not isinstance(image, CloudinaryResource):
        image = staticfiles_storage.stored_name(image)
        image = CloudinaryResource(image)
    return mark_safe(image.image(**options))
