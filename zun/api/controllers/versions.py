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


from webob import exc

from zun.common.i18n import _

# NOTE(yuntong): v1.0 is reserved to indicate Ocata's API, but is not presently
#             supported by the API service. All changes between Ocata and the
#             point where we added microversioning are considered backwards-
#             compatible, but are not specifically discoverable at this time.
#
#             The v1.1 version indicates this "initial" version as being
#             different from Ocata (v1.0), and includes the following changes:
#
#             Add details of new api versions here:

#
# For each newly added microversion change, update the API version history
# string below with a one or two line description. Also update
# rest_api_version_history.rst for extra information on microversion.
REST_API_VERSION_HISTORY = """REST API Version History:

    * 1.1 - Initial version
    * 1.2 - Support user specify pre created networks
    * 1.3 - Add auto_remove to container
    * 1.4 - Support list all container host and show a container host
    * 1.5 - Add runtime to container
    * 1.6 - Support detach network from a container
    * 1.7 - Disallow non-admin users to force delete containers
    * 1.8 - Support attach a network to a container
    * 1.9 - Add support set container's hostname
    * 1.10 - Make delete container async
    * 1.11 - Add mounts to container create
    * 1.12 - Add support to stop container before delete
    * 1.13 - Add support for listing networks of a container
    * 1.14 - Add support to rename the container from update api
    * 1.15 - Remove add_security_group and remove_security_group
    * 1.16 - Modify restart_policy to capsule spec content
    * 1.17 - Add support for detaching ports
    * 1.18 - Modify the response of network list
    * 1.19 - Intoduce container resize API
    * 1.20 - Convert type of 'command' from string to list
"""

BASE_VER = '1.1'
CURRENT_MAX_VER = '1.20'


class Version(object):
    """API Version object."""

    string = 'OpenStack-API-Version'
    """HTTP Header string carrying the requested version"""

    min_string = 'OpenStack-API-Minimum-Version'
    """HTTP response header"""

    max_string = 'OpenStack-API-Maximum-Version'
    """HTTP response header"""

    service_string = 'container'

    def __init__(self, headers, default_version, latest_version,
                 from_string=None):
        """Create an API Version object from the supplied headers.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :param from_string: create the version from string not headers
        :raises: webob.HTTPNotAcceptable
        """
        if from_string:
            (self.major, self.minor) = tuple(int(i)
                                             for i in from_string.split('.'))

        else:
            (self.major, self.minor) = Version.parse_headers(headers,
                                                             default_version,
                                                             latest_version)

    def __repr__(self):
        return '%s.%s' % (self.major, self.minor)

    @staticmethod
    def parse_headers(headers, default_version, latest_version):
        """Determine the API version requested based on the headers supplied.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :returns: a tuple of (major, minor) version numbers
        :raises: webob.HTTPNotAcceptable
        """

        version_hdr = headers.get(Version.string, default_version)

        try:
            version_service, version_str = version_hdr.split()
        except ValueError:
            raise exc.HTTPNotAcceptable(_(
                "Invalid service type for %s header") % Version.string)

        if version_str.lower() == 'latest':
            version_service, version_str = latest_version.split()

        if version_service != Version.service_string:
            raise exc.HTTPNotAcceptable(_(
                "Invalid service type for %s header") % Version.string)
        try:
            version = tuple(int(i) for i in version_str.split('.'))
        except ValueError:
            version = ()

        if len(version) != 2:
            raise exc.HTTPNotAcceptable(_(
                "Invalid value for %s header") % Version.string)
        return version

    def is_null(self):
        return self.major == 0 and self.minor == 0

    def matches(self, start_version, end_version):
        if self.is_null():
            raise ValueError

        return start_version <= self <= end_version

    def __lt__(self, other):
        if self.major < other.major:
            return True
        if self.major == other.major and self.minor < other.minor:
            return True
        return False

    def __gt__(self, other):
        if self.major > other.major:
            return True
        if self.major == other.major and self.minor > other.minor:
            return True
        return False

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor

    def __le__(self, other):
        return self < other or self == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return self > other or self == other
