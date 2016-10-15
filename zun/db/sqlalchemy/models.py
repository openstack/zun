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

from oslo_config import cfg
from oslo_db.sqlalchemy import models
import six.moves.urllib.parse as urlparse
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import schema
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator, TEXT


def table_args():
    engine_name = urlparse.urlparse(cfg.CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': cfg.CONF.database.mysql_engine,
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
    task_state = Column(String(20))
    environment = Column(JSONEncodedDict)
    workdir = Column(String(255))
    ports = Column(JSONEncodedList)
    hostname = Column(String(255))
    labels = Column(JSONEncodedDict)


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
