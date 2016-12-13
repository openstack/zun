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

from oslo_log import log as logging
from oslo_utils import timeutils
import pecan
from pecan import rest

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers import types
from zun.api.controllers.v1 import collection
from zun.api import utils as api_utils
from zun.common import exception
from zun.common.i18n import _LE
from zun.common import policy
from zun.common import utils
from zun import objects

LOG = logging.getLogger(__name__)


class Image(base.APIBase):
    """API representation of an image.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    an image.
    """

    fields = {
        'uuid': {
            'validate': types.Uuid.validate,
        },
        'image_id': {
            'validate': types.NameType.validate,
            'validate_args': {
                'pattern': types.image_name_pattern
            },
        },
        'repo': {
            'validate': types.NameType.validate,
            'validate_args': {
                'pattern': types.image_name_pattern
            },
            'mandatory': True
        },
        'tag': {
            'validate': types.NameType.validate,
            'validate_args': {
                'pattern': types.image_name_pattern
            },
        },
        'size': {
            'validate': types.ImageSize.validate,
        },
    }

    def __init__(self, **kwargs):
        super(Image, self).__init__(**kwargs)

    @staticmethod
    def _convert_with_links(image, url, expand=True):
        if not expand:
            image.unset_fields_except([
                'uuid', 'image_id', 'repo', 'tag', 'size'])

        image.links = [link.Link.make_link(
            'self', url,
            'images', image.uuid),
            link.Link.make_link(
                'bookmark', url,
                'images', image.uuid,
                bookmark=True)]
        return image

    @classmethod
    def convert_with_links(cls, rpc_image, expand=True):
        image = Image(**rpc_image)
        return cls._convert_with_links(image, pecan.request.host_url,
                                       expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f35c',
                     repo='ubuntu',
                     tag='latest',
                     size='700m',
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9517', expand)


class ImageCollection(collection.Collection):
    """API representation of a collection of images."""

    fields = {
        'images': {
            'validate': types.List(types.Custom(Image)).validate,
        },
    }

    """A list containing images objects"""

    def __init__(self, **kwargs):
        self._type = 'images'

    @staticmethod
    def convert_with_links(rpc_images, limit, url=None,
                           expand=False, **kwargs):
        collection = ImageCollection()
        # TODO(sbiswas7): This is the ugly part of the deal.
        # We need to convert this p thing below as dict for now
        # Removal of dict-compat lead to this change.
        collection.images = [Image.convert_with_links(p.as_dict(), expand)
                             for p in rpc_images]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.images = [Image.sample(expand=False)]
        return sample


class ImagesController(rest.RestController):
    '''Controller for Images'''

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        '''Retrieve a list of images.'''
        context = pecan.request.context
        policy.enforce(context, "image:get_all",
                       action="image:get_all")
        return self._get_images_collection(**kwargs)

    def _get_images_collection(self, **kwargs):
        context = pecan.request.context
        limit = api_utils.validate_limit(kwargs.get('limit', None))
        sort_dir = api_utils.validate_sort_dir(kwargs.get('sort_dir', 'asc'))
        sort_key = kwargs.get('sort_key', 'id')
        resource_url = kwargs.get('resource_url', None)
        expand = kwargs.get('expand', None)
        filters = None
        marker_obj = None
        marker = kwargs.get('marker', None)
        if marker:
            marker_obj = objects.Image.get_by_uuid(context, marker)
        images = objects.Image.list(context,
                                    limit,
                                    marker_obj,
                                    sort_key,
                                    sort_dir,
                                    filters=filters)
        for i, c in enumerate(images):
            try:
                images[i] = pecan.request.rpcapi.image_show(context, c)
            except Exception as e:
                LOG.exception(_LE("Error while list image %(uuid)s: "
                                  "%(e)s."), {'uuid': c.uuid, 'e': e})

        return ImageCollection.convert_with_links(images, limit,
                                                  url=resource_url,
                                                  expand=expand,
                                                  sort_key=sort_key,
                                                  sort_dir=sort_dir)

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    def post(self, **image_dict):
        """Create a new image.

        :param image: an image within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, "image:pull",
                       action="image:pull")
        image_dict = Image(**image_dict).as_dict()
        image_dict['project_id'] = context.project_id
        image_dict['user_id'] = context.user_id
        repo_tag = image_dict.get('repo')
        image_dict['repo'], image_dict['tag'] = utils.parse_image_name(
            repo_tag)
        new_image = objects.Image(context, **image_dict)
        new_image.pull(context)
        pecan.request.rpcapi.image_pull(context, new_image)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('images', new_image.uuid)
        pecan.response.status = 202
        # TODO(sbiswas7): Schema validation is a better approach than
        # back n forth conversion into dicts and objects.
        return Image.convert_with_links(new_image.as_dict())
