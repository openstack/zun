#    Copyright 2017 ARM Holdings.
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
Experimental of the Zun API

NOTE: IN PROGRESS AND NOT FULLY IMPLEMENTED.
"""

from oslo_log import log as logging
import pecan

from zun.api.controllers import base as controllers_base
from zun.api.controllers.experimental import capsules as capsule_controller
from zun.api.controllers import link
from zun.api.controllers import versions as ver
from zun.api import http_error
from zun.common.i18n import _

LOG = logging.getLogger(__name__)


BASE_VERSION = 1

MIN_VER_STR = '%s %s' % (ver.Version.service_string, ver.BASE_VER)

MAX_VER_STR = '%s %s' % (ver.Version.service_string, ver.CURRENT_MAX_VER)

MIN_VER = ver.Version({ver.Version.string: MIN_VER_STR},
                      MIN_VER_STR, MAX_VER_STR)
MAX_VER = ver.Version({ver.Version.string: MAX_VER_STR},
                      MIN_VER_STR, MAX_VER_STR)


class MediaType(controllers_base.APIBase):
    """A media type representation."""

    fields = (
        'base',
        'type',
    )


class Experimental(controllers_base.APIBase):
    """The representation of the version experimental of the API."""

    fields = (
        'id',
        'media_types',
        'links',
        'capsules'
    )

    @staticmethod
    def convert():
        experimental = Experimental()
        experimental.id = "experimental"
        experimental.links = [link.make_link('self', pecan.request.host_url,
                                             'experimental', '',
                                             bookmark=True),
                              link.make_link('describedby',
                                             'https://docs.openstack.org',
                                             'developer/zun/dev',
                                             'api-spec-v1.html',
                                             bookmark=True,
                                             type='text/html')]
        experimental.media_types = \
            [MediaType(base='application/json',
                       type='application/vnd.openstack.'
                            'zun.experimental+json')]
        experimental.capsules = [link.make_link('self',
                                                pecan.request.host_url,
                                                'experimental/capsules', '',
                                                bookmark=True),
                                 link.make_link('bookmark',
                                                pecan.request.host_url,
                                                'capsules', '',
                                                bookmark=True)]
        return experimental


class Controller(controllers_base.Controller):
    """Version expereimental API controller root."""

    capsules = capsule_controller.CapsuleController()

    @pecan.expose('json')
    def get(self):
        return Experimental.convert()

    def _check_version(self, version, headers=None):
        if headers is None:
            headers = {}
        # ensure that major version in the URL matches the header
        if version.major != BASE_VERSION:
            raise http_error.HTTPNotAcceptableAPIVersion(_(
                "Mutually exclusive versions requested. Version %(ver)s "
                "requested but not supported by this service. "
                "The supported version range is: "
                "[%(min)s, %(max)s].") % {'ver': version,
                                          'min': MIN_VER_STR,
                                          'max': MAX_VER_STR},
                headers=headers,
                max_version=str(MAX_VER),
                min_version=str(MIN_VER))
        # ensure the minor version is within the supported range
        if version < MIN_VER or version > MAX_VER:
            raise http_error.HTTPNotAcceptableAPIVersion(_(
                "Version %(ver)s was requested but the minor version is not "
                "supported by this service. The supported version range is: "
                "[%(min)s, %(max)s].") % {'ver': version, 'min': MIN_VER_STR,
                                          'max': MAX_VER_STR},
                headers=headers,
                max_version=str(MAX_VER),
                min_version=str(MIN_VER))

    @pecan.expose()
    def _route(self, args):
        version = ver.Version(
            pecan.request.headers, MIN_VER_STR, MAX_VER_STR)

        # Always set the basic version headers
        pecan.response.headers[ver.Version.min_string] = MIN_VER_STR
        pecan.response.headers[ver.Version.max_string] = MAX_VER_STR
        pecan.response.headers[ver.Version.string] = " ".join(
            [ver.Version.service_string, str(version)])
        pecan.response.headers["vary"] = ver.Version.string

        # assert that requested version is supported
        self._check_version(version, pecan.response.headers)
        pecan.request.version = version
        if pecan.request.body:
            msg = ("Processing request: url: %(url)s, %(method)s, "
                   "body: %(body)s" %
                   {'url': pecan.request.url,
                    'method': pecan.request.method,
                    'body': pecan.request.body})
            LOG.debug(msg)

        return super(Controller, self)._route(args)

__all__ = (Controller)
