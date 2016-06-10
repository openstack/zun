# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Base classes for storage engines
"""

import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six


_BACKEND_MAPPING = {'sqlalchemy': 'zun.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    @abc.abstractmethod
    def destroy_zun_service(self, zun_service_id):
        """Destroys a zun_service record.

        :param zun_service_id: The id of a zun_service.
        """

    @abc.abstractmethod
    def update_zun_service(self, zun_service_id, values):
        """Update properties of a zun_service.

        :param zun_service_id: The id of a zun_service record.
        """

    @abc.abstractmethod
    def get_zun_service_by_host_and_binary(self, context, host, binary):
        """Return a zun_service record.

        :param context: The security context
        :param host: The host where the binary is located.
        :param binary: The name of the binary.
        :returns: A zun_service record.
        """

    @abc.abstractmethod
    def create_zun_service(self, values):
        """Create a new zun_service record.

        :param values: A dict containing several items used to identify
                       and define the zun_service record.
        :returns: A zun_service record.
        """

    @abc.abstractmethod
    def get_zun_service_list(self, context, disabled=None, limit=None,
                             marker=None, sort_key=None, sort_dir=None):
        """Get matching zun_service records.

        Return a list of the specified columns for all zun_services
        those match the specified filters.

        :param context: The security context
        :param disabled: Filters disbaled services. Defaults to None.
        :param limit: Maximum number of zun_services to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """
