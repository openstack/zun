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
SQLAlchemy models for container service
"""

import json

from oslo_db.sqlalchemy import models
import six.moves.urllib.parse as urlparse
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import orm
from sqlalchemy import schema
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator, TEXT

import zun.conf


def table_args():
    engine_name = urlparse.urlparse(zun.conf.CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': zun.conf.CONF.database.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class JsonEncodedType(TypeDecorator):
    """Abstract base type serialized as json-encoded string in db."""
    type = None
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            # Save default value according to current type to keep the
            # interface the consistent.
            value = self.type()
        elif not isinstance(value, self.type):
            raise TypeError("%s supposes to store %s objects, but %s given"
                            % (self.__class__.__name__,
                               self.type.__name__,
                               type(value).__name__))
        serialized_value = json.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class JSONEncodedDict(JsonEncodedType):
    """Represents dict serialized as json-encoded string in db."""
    type = dict


class JSONEncodedList(JsonEncodedType):
    """Represents list serialized as json-encoded string in db."""
    type = list


class ZunBase(models.TimestampMixin,
              models.ModelBase):

    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d

    def save(self, session=None):
        import zun.db.sqlalchemy.api as db_api

        if session is None:
            session = db_api.get_session()

        super(ZunBase, self).save(session)


Base = declarative_base(cls=ZunBase)


class ZunService(Base):
    """Represents health status of various zun services"""
    __tablename__ = 'zun_service'
    __table_args__ = (
        schema.UniqueConstraint("host", "binary",
                                name="uniq_zun_service0host0binary"),
        table_args()
    )

    id = Column(Integer, primary_key=True)
    host = Column(String(255))
    binary = Column(String(255))
    disabled = Column(Boolean, default=False)
    disabled_reason = Column(String(255))
    last_seen_up = Column(DateTime, nullable=True)
    forced_down = Column(Boolean, default=False)
    report_count = Column(Integer, nullable=False, default=0)


class Container(Base):
    """Represents a container."""

    __tablename__ = 'container'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_container0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    user_id = Column(String(255))
    uuid = Column(String(36))
    container_id = Column(String(36))
    name = Column(String(255))
    image = Column(String(255))
    cpu = Column(Float)
    command = Column(String(255))
    memory = Column(String(255))
    status = Column(String(20))
    status_reason = Column(Text, nullable=True)
    task_state = Column(String(20))
    environment = Column(JSONEncodedDict)
    workdir = Column(String(255))
    ports = Column(JSONEncodedList)
    hostname = Column(String(63))
    labels = Column(JSONEncodedDict)
    meta = Column(JSONEncodedDict)
    addresses = Column(JSONEncodedDict)
    image_pull_policy = Column(Text, nullable=True)
    host = Column(String(255))
    restart_policy = Column(JSONEncodedDict)
    status_detail = Column(String(50))
    interactive = Column(Boolean, default=False)
    image_driver = Column(String(255))
    websocket_url = Column(String(255))
    websocket_token = Column(String(255))
    security_groups = Column(JSONEncodedList)


class Image(Base):
    """Represents an image. """

    __tablename__ = 'image'
    __table_args__ = (
        schema.UniqueConstraint('repo', 'tag', name='uniq_image0repotag'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    user_id = Column(String(255))
    uuid = Column(String(36))
    image_id = Column(String(255))
    repo = Column(String(255))
    tag = Column(String(255))
    size = Column(String(255))


class ResourceProvider(Base):
    """Represents an resource provider. """

    __tablename__ = 'resource_provider'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_resource_provider0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True, nullable=False)
    uuid = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    root_provider = Column(String(36), nullable=False)
    parent_provider = Column(String(36), nullable=True)
    can_host = Column(Integer, default=0)


class ResourceClass(Base):
    """Represents an resource class. """

    __tablename__ = 'resource_class'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_resource_class0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True, nullable=False)
    uuid = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)


class Inventory(Base):
    """Represents an inventory. """

    __tablename__ = 'inventory'
    __table_args__ = (
        Index('inventory_resource_provider_id_idx',
              'resource_provider_id'),
        Index('inventory_resource_class_id_idx',
              'resource_class_id'),
        Index('inventory_resource_provider_resource_class_idx',
              'resource_provider_id', 'resource_class_id'),
        schema.UniqueConstraint(
            'resource_provider_id', 'resource_class_id',
            name='uniq_inventory0resource_provider_resource_class'),
        table_args()
    )
    id = Column(Integer, primary_key=True, nullable=False)
    resource_provider_id = Column(Integer, nullable=False)
    resource_class_id = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    reserved = Column(Integer, nullable=False)
    min_unit = Column(Integer, nullable=False)
    max_unit = Column(Integer, nullable=False)
    step_size = Column(Integer, nullable=False)
    allocation_ratio = Column(Float, nullable=False)
    is_nested = Column(Integer, nullable=False)
    blob = Column(JSONEncodedList)
    resource_provider = orm.relationship(
        "ResourceProvider",
        primaryjoin=('and_(Inventory.resource_provider_id == '
                     'ResourceProvider.id)'),
        foreign_keys=resource_provider_id)


class Allocation(Base):
    """Represents an allocation. """

    __tablename__ = 'allocation'
    __table_args__ = (
        Index('allocation_resource_provider_class_used_idx',
              'resource_provider_id', 'resource_class_id', 'used'),
        Index('allocation_resource_class_id_idx', 'resource_class_id'),
        Index('allocation_consumer_id_idx', 'consumer_id'),
        table_args()
    )
    id = Column(Integer, primary_key=True, nullable=False)
    resource_provider_id = Column(Integer, nullable=False)
    resource_class_id = Column(Integer, nullable=False)
    consumer_id = Column(String(36), nullable=False)
    used = Column(Integer, nullable=False)
    is_nested = Column(Integer, nullable=False)
    blob = Column(JSONEncodedList)
    resource_provider = orm.relationship(
        "ResourceProvider",
        primaryjoin=('and_(Allocation.resource_provider_id == '
                     'ResourceProvider.id)'),
        foreign_keys=resource_provider_id)


class ComputeNode(Base):
    """Represents a compute node. """

    __tablename__ = 'compute_node'
    __table_args__ = (
        table_args()
    )
    uuid = Column(String(36), primary_key=True, nullable=False)
    hostname = Column(String(255), nullable=False)
    numa_topology = Column(JSONEncodedDict, nullable=True)
    mem_total = Column(Integer, nullable=False, default=0)
    mem_free = Column(Integer, nullable=False, default=0)
    mem_available = Column(Integer, nullable=False, default=0)
    total_containers = Column(Integer, nullable=False, default=0)
    running_containers = Column(Integer, nullable=False, default=0)
    paused_containers = Column(Integer, nullable=False, default=0)
    stopped_containers = Column(Integer, nullable=False, default=0)
    cpus = Column(Integer, nullable=False, default=0)
    cpu_used = Column(Float, nullable=False, default=0.0)
    architecture = Column(String(32), nullable=True)
    os_type = Column(String(32), nullable=True)
    os = Column(String(64), nullable=True)
    kernel_version = Column(String(128), nullable=True)
    labels = Column(JSONEncodedDict)
