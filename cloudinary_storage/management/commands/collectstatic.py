from django.contrib.staticfiles.management.commands import collectstatic


class Command(collectstatic.Command):
    def delete_file(self, path, prefixed_path, source_storage):
        return True
