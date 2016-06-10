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

"""SQLAlchemy storage backend."""

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_utils import timeutils
from sqlalchemy.orm.exc import NoResultFound

from zun.common import exception
from zun.common.i18n import _
from zun.common import utils
from zun.db import api
from zun.db.sqlalchemy import models

CONF = cfg.CONF


_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if utils.is_int_like(value):
        return query.filter_by(id=value)
    elif utils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    try:
        query = db_utils.paginate_query(query, model, limit, sort_keys,
                                        marker=marker, sort_dir=sort_dir)
    except db_exc.InvalidSortKey:
        raise exception.InvalidParameterValue(
            _('The sort_key value "%(key)s" is an invalid field for sorting')
            % {'key': sort_key})
    return query.all()


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def destroy_zun_service(self, zun_service_id):
        session = get_session()
        with session.begin():
            query = model_query(models.ZunService, session=session)
            query = add_identity_filter(query, zun_service_id)
            count = query.delete()
            if count != 1:
                raise exception.ZunServiceNotFound(zun_service_id)

    def update_zun_service(self, zun_service_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ZunService, session=session)
            query = add_identity_filter(query, zun_service_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ZunServiceNotFound(zun_service_id)

            if 'report_count' in values:
                if values['report_count'] > ref.report_count:
                    ref.last_seen_up = timeutils.utcnow()

            ref.update(values)
        return ref

    def get_zun_service_by_host_and_binary(self, context, host, binary):
        query = model_query(models.ZunService)
        query = query.filter_by(host=host, binary=binary)
        try:
            return query.one()
        except NoResultFound:
            return None

    def create_zun_service(self, values):
        zun_service = models.ZunService()
        zun_service.update(values)
        try:
            zun_service.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ZunServiceAlreadyExists(
                id=zun_service['id'])
        return zun_service

    def get_zun_service_list(self, context, disabled=None, limit=None,
                             marker=None, sort_key=None, sort_dir=None
                             ):
        query = model_query(models.ZunService)
        if disabled:
            query = query.filter_by(disabled=disabled)

        return _paginate_query(models.ZunService, limit, marker,
                               sort_key, sort_dir, query)
