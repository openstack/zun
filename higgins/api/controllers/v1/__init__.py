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
Version 1 of the Higgins API

NOTE: IN PROGRESS AND NOT FULLY IMPLEMENTED.
"""

from oslo_log import log as logging
import pecan
from pecan import rest
from wsme import types as wtypes

from higgins.api.controllers import base as controllers_base
from higgins.api.controllers import link
from higgins.api import expose

LOG = logging.getLogger(__name__)


class MediaType(controllers_base.APIBase):
    """A media type representation."""

    base = wtypes.text
    type = wtypes.text

    def __init__(self, base, type):
        self.base = base
        self.type = type


class V1(controllers_base.APIBase):
    """The representation of the version 1 of the API."""

    id = wtypes.text
    """The ID of the version, also acts as the release number"""

    media_types = [MediaType]
    """An array of supcontainersed media types for this version"""

    links = [link.Link]
    """Links that point to a specific URL for this version and documentation"""

    @staticmethod
    def convert():
        v1 = V1()
        v1.id = "v1"
        v1.links = [link.Link.make_link('self', pecan.request.host_url,
                                        'v1', '', bookmark=True),
                    link.Link.make_link('describedby',
                                        'http://docs.openstack.org',
                                        'developer/higgins/dev',
                                        'api-spec-v1.html',
                                        bookmark=True, type='text/html')]
        v1.media_types = [MediaType('application/json',
                          'application/vnd.openstack.higgins.v1+json')]
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    @expose.expose(V1)
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
