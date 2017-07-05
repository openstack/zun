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
from oslo_serialization import jsonutils as json

from zun.common import exception
import zun.db.etcd as db
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

    def path_already_exist(self, client, path):
        try:
            client.read(path)
        except etcd.EtcdKeyNotFound:
            return False

        return True

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in values.items():
            setattr(self, k, v)

    def save(self, session=None):
        if session is None:
            session = db.api.get_connection()
        client = session.client
        path = self.etcd_path(self.uuid)

        if self.path_already_exist(client, path):
            raise exception.ResourceExists(name=getattr(self, '__class__'))

        client.write(path, json.dump_as_bytes(self.as_dict()))
        return


class ZunService(Base):
    """Represents health status of various zun services"""

    _path = '/zun_services'

    _fields = objects.ZunService.fields.keys()

    def __init__(self, service_data):
        self.path = ZunService.path()
        for f in ZunService.fields():
            setattr(self, f, None)
        self.id = 1
        self.disabled = False
        self.forced_down = False
        self.report_count = 0
        self.update(service_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields

    def save(self, session=None):
        if session is None:
            session = db.api.get_connection()
        client = session.client
        path = self.etcd_path(self.host + '_' + self.binary)

        if self.path_already_exist(client, path):
            raise exception.ZunServiceAlreadyExists(host=self.host,
                                                    binary=self.binary)

        client.write(path, json.dump_as_bytes(self.as_dict()))
        return


class Container(Base):
    """Represents a container."""

    _path = '/containers'

    _fields = objects.Container.fields.keys()

    def __init__(self, container_data):
        self.path = Container.path()
        for f in Container.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(container_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class Image(Base):
    """Represents a container image."""

    _path = '/images'

    _fields = objects.Image.fields.keys()

    def __init__(self, image_data):
        self.path = Image.path()
        for f in Image.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(image_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class ResourceClass(Base):
    """Represents a resource class."""

    _path = '/resource_classes'

    _fields = objects.ResourceClass.fields.keys()

    def __init__(self, resource_class_data):
        self.path = ResourceClass.path()
        for f in ResourceClass.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(resource_class_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields
