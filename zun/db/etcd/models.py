#    Copyright 2016 IBM, Corp.
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
etcd models
"""

import etcd
import six

from zun.common import exception
from zun import objects


class Base(object):

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key):
        return getattr(self, key)

    def etcd_path(self, sub_path):
        return self.path + '/' + sub_path

    def as_dict(self):
        d = {}
        for f in self._fields:
            d[f] = getattr(self, f, None)

        return d

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in six.iteritems(values):
            setattr(self, k, v)

    def save(self, session=None):
        import zun.db.etcd.api as db_api

        if session is None:
            session = db_api.get_connection()

        try:
            session.client.read(self.etcd_path(self.uuid))
        except etcd.EtcdKeyNotFound:
            session.client.write(self.etcd_path(self.uuid), self.as_dict())
            return

        raise exception.ContainerAlreadyExists(uuid=self.uuid)


class ZunService(Base):
    """Represents health status of various zun services"""

    _path = '/zun_service'

    _fields = objects.ZunService.fields.keys()

    def __init__(self, service_data):
        self.path = ZunService.path()
        for f in ZunService.fields():
            setattr(self, f, None)
        self.update(service_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class Container(Base):
    """Represents a container."""

    _path = '/containers'

    _fields = objects.Container.fields.keys()

    def __init__(self, container_data):
        self.path = Container.path()
        for f in Container.fields():
            setattr(self, f, None)
        self.update(container_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields
