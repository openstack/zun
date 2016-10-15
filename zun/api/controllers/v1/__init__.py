# All Rights Reserved.
#
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

"""
Version 1 of the Zun API

NOTE: IN PROGRESS AND NOT FULLY IMPLEMENTED.
"""

from oslo_log import log as logging
import pecan
from pecan import rest

from zun.api.controllers import base as controllers_base
from zun.api.controllers import link
from zun.api.controllers import types
from zun.api.controllers.v1 import containers as container_controller
from zun.api.controllers.v1 import images as image_controller
from zun.api.controllers.v1 import zun_services

LOG = logging.getLogger(__name__)


class MediaType(controllers_base.APIBase):
    """A media type representation."""

    fields = {
        'base': {
            'validate': types.Text.validate
        },
        'type': {
            'validate': types.Text.validate
        },
    }


class V1(controllers_base.APIBase):
    """The representation of the version 1 of the API."""

    fields = {
        'id': {
            'validate': types.Text.validate
        },
        'media_types': {
            'validate': types.List(types.Custom(MediaType)).validate
        },
        'links': {
            'validate': types.List(types.Custom(link.Link)).validate
        },
        'services': {
            'validate': types.List(types.Custom(link.Link)).validate
        },
        'containers': {
            'validate': types.List(types.Custom(link.Link)).validate
        },
        'images': {
            'validate': types.List(types.Custom(link.Link)).validate
        },
    }

    @staticmethod
    def convert():
        v1 = V1()
        v1.id = "v1"
        v1.links = [link.Link.make_link('self', pecan.request.host_url,
                                        'v1', '', bookmark=True),
                    link.Link.make_link('describedby',
                                        'http://docs.openstack.org',
                                        'developer/zun/dev',
                                        'api-spec-v1.html',
                                        bookmark=True, type='text/html')]
        v1.media_types = [MediaType(base='application/json',
                          type='application/vnd.openstack.zun.v1+json')]
        v1.services = [link.Link.make_link('self', pecan.request.host_url,
                                           'services', ''),
                       link.Link.make_link('bookmark',
                                           pecan.request.host_url,
                                           'services', '',
                                           bookmark=True)]
        v1.containers = [link.Link.make_link('self', pecan.request.host_url,
                                             'containers', ''),
                         link.Link.make_link('bookmark',
                                             pecan.request.host_url,
                                             'containers', '',
                                             bookmark=True)]
        v1.images = [link.Link.make_link('self', pecan.request.host_url,
                                         'images', ''),
                     link.Link.make_link('bookmark',
                                         pecan.request.host_url,
                                         'images', '',
                                         bookmark=True)]
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    services = zun_services.ZunServiceController()
    containers = container_controller.ContainersController()
    images = image_controller.ImagesController()

    @pecan.expose('json')
    def get(self):
        return V1.convert()

    @pecan.expose()
    def _route(self, args):
        if pecan.request.body:
            msg = ("Processing request: url: %(url)s, %(method)s, "
                   "body: %(body)s" %
                   {'url': pecan.request.url,
                    'method': pecan.request.method,
                    'body': pecan.request.body})
            LOG.debug(msg)

        return super(Controller, self)._route(args)

__all__ = (Controller)
