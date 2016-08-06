import cloudinary.api


def get_resources_by_path(resource_type, tag, path):
    resources = []
    next_cursor = None
    while True:
        options = {
            'type': 'upload',
            'prefix': path,
            'resource_type': resource_type,
            'max_results': 500,
            'tags': True
        }
        if next_cursor is not None:
            options['next_cursor'] = next_cursor
        response = cloudinary.api.resources(**options)
        for resource in response['resources']:
            if tag in resource['tags']:
                resources.append(resource['public_id'])
        next_cursor = response.get('next_cursor')
        if next_cursor is None:
            break
    return resources


def get_resources(resource_type, tag):
    resources = []
    next_cursor = None
    while True:
        options = {'resource_type': resource_type, 'max_results': 500}
        if next_cursor is not None:
            options['next_cursor'] = next_cursor
        response = cloudinary.api.resources_by_tag(tag, **options)
        for resource in response['resources']:
            resources.append(resource['public_id'])
        next_cursor = response.get('next_cursor')
        if next_cursor is None:
            break
    return resources
