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


_BACKEND_MAPPING = {'sqlalchemy': 'higgins.db.sqlalchemy.api'}
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
    def destroy_higgins_service(self, higgins_service_id):
        """Destroys a higgins_service record.

        :param higgins_service_id: The id of a higgins_service.
        """

    @abc.abstractmethod
    def update_higgins_service(self, higgins_service_id, values):
        """Update properties of a higgins_service.

        :param higgins_service_id: The id of a higgins_service record.
        """

    @abc.abstractmethod
    def get_higgins_service_by_host_and_binary(self, context, host, binary):
        """Return a higgins_service record.

        :param context: The security context
        :param host: The host where the binary is located.
        :param binary: The name of the binary.
        :returns: A higgins_service record.
        """

    @abc.abstractmethod
    def create_higgins_service(self, values):
        """Create a new higgins_service record.

        :param values: A dict containing several items used to identify
                       and define the higgins_service record.
        :returns: A higgins_service record.
        """

    @abc.abstractmethod
    def get_higgins_service_list(self, context, disabled=None, limit=None,
                                 marker=None, sort_key=None, sort_dir=None):
        """Get matching higgins_service records.

        Return a list of the specified columns for all higgins_services
        those match the specified filters.

        :param context: The security context
        :param disabled: Filters disbaled services. Defaults to None.
        :param limit: Maximum number of higgins_services to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """
