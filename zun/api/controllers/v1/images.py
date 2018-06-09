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
from oslo_utils import strutils
import pecan

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import images as schema
from zun.api.controllers.v1.views import images_view as view
from zun.api import utils as api_utils
from zun.api import validation
from zun.common import exception
from zun.common.i18n import _
from zun.common import policy
from zun.common import utils
from zun import objects

LOG = logging.getLogger(__name__)


def check_policy_on_image(image, action):
    context = pecan.request.context
    policy.enforce(context, action, image, action=action)


def _get_host(host_ident):
    try:
        return api_utils.get_resource('ComputeNode', host_ident)
    except exception.ComputeNodeNotFound:
        msg = _("The host %s does not exist.") % host_ident
        raise exception.InvalidValue(msg)


class ImageCollection(collection.Collection):
    """API representation of a collection of images."""

    fields = {
        'images',
        'next'
    }

    """A list containing images objects"""

    def __init__(self, **kwargs):
        super(ImageCollection, self).__init__(**kwargs)
        self._type = 'images'

    @staticmethod
    def convert_with_links(rpc_images, limit, url=None,
                           expand=False, **kwargs):
        collection = ImageCollection()
        collection.images = [view.format_image(url, p) for p in rpc_images]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class ImagesController(base.Controller):
    """Controller for Images"""

    _custom_actions = {
        'search': ['GET']
    }

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_delete)
    def delete(self, image_id, **kwargs):
        context = pecan.request.context
        policy.enforce(context, "image:delete", action="image:delete")
        host = _get_host(kwargs.pop('host'))
        image = utils.get_image(image_id)
        return pecan.request.compute_api.image_delete(context, image,
                                                      host.hostname)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        """Retrieve a list of images."""
        context = pecan.request.context
        policy.enforce(context, "image:get_all",
                       action="image:get_all")
        return self._get_images_collection(**kwargs)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_one(self, image_id):
        """Retrieve information about the given image.

        :param image_id: UUID of a image.
        """
        image = utils.get_image(image_id)
        check_policy_on_image(image.as_dict(), "image:get_one")
        return view.format_image(pecan.request.host_url, image)

    def _get_images_collection(self, **kwargs):
        context = pecan.request.context
        limit = api_utils.validate_limit(kwargs.get('limit'))
        sort_dir = api_utils.validate_sort_dir(kwargs.get('sort_dir', 'asc'))
        sort_key = kwargs.get('sort_key', 'id')
        resource_url = kwargs.get('resource_url')
        expand = kwargs.get('expand')
        filters = None
        marker_obj = None
        marker = kwargs.get('marker')
        if marker:
            marker_obj = objects.Image.get_by_uuid(context, marker)
        images = objects.Image.list(context,
                                    limit,
                                    marker_obj,
                                    sort_key,
                                    sort_dir,
                                    filters=filters)
        return ImageCollection.convert_with_links(images, limit,
                                                  url=resource_url,
                                                  expand=expand,
                                                  sort_key=sort_key,
                                                  sort_dir=sort_dir)

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.image_create)
    def post(self, **image_dict):
        """Create a new image.

        :param image_dict: an image within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, "image:pull",
                       action="image:pull")
        host = _get_host(image_dict.pop('host'))
        image_dict['project_id'] = context.project_id
        image_dict['user_id'] = context.user_id
        repo_tag = image_dict.get('repo')
        image_dict['repo'], image_dict['tag'] = utils.parse_image_name(
            repo_tag)
        new_image = objects.Image(context, **image_dict)
        new_image.pull(context)
        pecan.request.compute_api.image_pull(context, new_image, host.hostname)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('images', new_image.uuid)
        pecan.response.status = 202
        return view.format_image(pecan.request.host_url, new_image)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_search)
    def search(self, image, image_driver=None, exact_match=False):
        """Search a specific image

        :param image:  Name of the image.
        :param image_driver: Name of the image driver (glance, docker).
        :param exact_match: if True, exact match the image name.
        """
        context = pecan.request.context
        policy.enforce(context, "image:search",
                       action="image:search")
        LOG.debug('Calling compute.image_search with %s', image)
        try:
            exact_match = strutils.bool_from_string(exact_match, strict=True)
        except ValueError:
            bools = ', '.join(strutils.TRUE_STRINGS + strutils.FALSE_STRINGS)
            raise exception.InvalidValue(_('Valid exact_match values are: %s')
                                         % bools)
        # Valiadtion accepts 'None' so need to convert it to None
        if image_driver:
            image_driver = api_utils.string_or_none(image_driver)

        return pecan.request.compute_api.image_search(context, image,
                                                      image_driver,
                                                      exact_match)
