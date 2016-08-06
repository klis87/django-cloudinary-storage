from django.test import SimpleTestCase

from cloudinary_storage.management.commands.deleteorphanedmedia import Command as DeleteOrphanedMediaCommand


class DeleteOrphanedMediaCommandTests(SimpleTestCase):
    def test_get_resource_types(self):
        command = DeleteOrphanedMediaCommand()
        self.assertEqual({'raw', 'image'}, command.get_resource_types())