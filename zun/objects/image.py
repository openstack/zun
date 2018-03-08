#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_versionedobjects import fields

from zun.db import api as dbapi
from zun.objects import base


@base.ZunObjectRegistry.register
class Image(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version = '1.1': Add delete image
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'image_id': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'repo': fields.StringField(nullable=True),
        'tag': fields.StringField(nullable=True),
        'size': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(image, db_image):
        """Converts a database entity to a formal object."""
        for field in image.fields:
            setattr(image, field, db_image[field])

        image.obj_reset_changes()
        return image

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Image._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find an image based on uuid and return a :class:`Image` object.

        :param uuid: the uuid of an image.
        :param context: Security context
        :returns: a :class:`Image` object.
        """
        db_image = dbapi.get_image_by_uuid(context, uuid)
        image = Image._from_db_object(cls(context), db_image)
        return image

    @base.remotable_classmethod
    def list(cls, context=None, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of Image objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filters when list images, the filter name could be
                        'repo', 'image_id', 'project_id', 'user_id', 'size'
        :returns: a list of :class:`Image` object.

        """
        db_images = dbapi.list_images(context,
                                      limit=limit,
                                      marker=marker,
                                      sort_key=sort_key,
                                      sort_dir=sort_dir,
                                      filters=filters)
        return Image._from_db_object_list(db_images, cls, context)

    @base.remotable
    def destroy(self, context, image_uuid):
        dbapi.destroy_image(context, image_uuid)
        self.obj_reset_changes()

    @base.remotable
    def pull(self, context=None):
        """Create an image record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Image(context)

        """
        values = self.obj_get_changes()
        db_image = dbapi.pull_image(context, values)
        self._from_db_object(self, db_image)

    @base.remotable
    def save(self, context=None):
        """Save updates to this Image.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Image(context)
        """
        updates = self.obj_get_changes()
        dbapi.update_image(self.uuid, updates)
        self.obj_reset_changes()
