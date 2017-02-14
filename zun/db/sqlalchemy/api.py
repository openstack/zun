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

from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

from zun.common import exception
from zun.common.i18n import _
import zun.conf
from zun.db.sqlalchemy import models

CONF = zun.conf.CONF

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
    if strutils.is_int_like(value):
        return query.filter_by(id=value)
    elif uuidutils.is_uuid_like(value):
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


class Connection(object):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_tenant_filters(self, context, query):
        if context.is_admin and context.all_tenants:
            return query

        if context.project_id:
            query = query.filter_by(project_id=context.project_id)
        else:
            query = query.filter_by(user_id=context.user_id)

        return query

    def _add_containers_filters(self, query, filters):
        if filters is None:
            filters = {}

        filter_names = ['name', 'image', 'project_id', 'user_id',
                        'memory', 'bay_uuid']
        for name in filter_names:
            if name in filters:
                query = query.filter_by(**{name: filters[name]})

        return query

    def list_container(self, context, filters=None, limit=None,
                       marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.Container)
        query = self._add_tenant_filters(context, query)
        query = self._add_containers_filters(query, filters)
        return _paginate_query(models.Container, limit, marker,
                               sort_key, sort_dir, query)

    def _validate_unique_container_name(self, context, name):
        if not CONF.compute.unique_container_name_scope:
            return
        lowername = name.lower()
        base_query = model_query(models.Container).\
            filter(func.lower(models.Container.name) == lowername)
        if CONF.compute.unique_container_name_scope == 'project':
            container_with_same_name = base_query.\
                filter_by(project_id=context.project_id).count()
        elif CONF.compute.unique_container_name_scope == 'global':
            container_with_same_name = base_query.count()
        else:
            return

        if container_with_same_name > 0:
            raise exception.ContainerAlreadyExists(field='name',
                                                   value=lowername)

    def create_container(self, context, values):
        # ensure defaults are present for new containers
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        if values.get('name'):
            self._validate_unique_container_name(context, values['name'])

        container = models.Container()
        container.update(values)
        try:
            container.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ContainerAlreadyExists(field='UUID',
                                                   value=values['uuid'])
        return container

    def get_container_by_uuid(self, context, container_uuid):
        query = model_query(models.Container)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=container_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ContainerNotFound(container=container_uuid)

    def get_container_by_name(self, context, container_name):
        query = model_query(models.Container)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=container_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ContainerNotFound(container=container_name)
        except MultipleResultsFound:
            raise exception.Conflict('Multiple containers exist with same '
                                     'name. Please use the container uuid '
                                     'instead.')

    def destroy_container(self, context, container_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            count = query.delete()
            if count != 1:
                raise exception.ContainerNotFound(container_id)

    def update_container(self, context, container_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Container.")
            raise exception.InvalidParameterValue(err=msg)

        if 'name' in values:
            self._validate_unique_container_name(context, values['name'])

        return self._do_update_container(container_id, values)

    def _do_update_container(self, container_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ContainerNotFound(container=container_id)

            ref.update(values)
        return ref

    def destroy_zun_service(self, host, binary):
        session = get_session()
        with session.begin():
            query = model_query(models.ZunService, session=session)
            query = query.filter_by(host=host, binary=binary)
            count = query.delete()
            if count != 1:
                raise exception.ZunServiceNotFound(host=host, binary=binary)

    def update_zun_service(self, host, binary, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ZunService, session=session)
            query = query.filter_by(host=host, binary=binary)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ZunServiceNotFound(host=host, binary=binary)

            if 'report_count' in values:
                if values['report_count'] > ref.report_count:
                    ref.last_seen_up = timeutils.utcnow()

            ref.update(values)
        return ref

    def get_zun_service(self, host, binary):
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
                host=zun_service.host, binary=zun_service.binary)
        return zun_service

    def _add_zun_service_filters(self, query, filters):
        if filters is None:
            filters = {}

        filter_names = ['disabled', 'host', 'binary', 'project_id', 'user_id']
        for name in filter_names:
            if name in filters:
                query = query.filter_by(**{name: filters[name]})

        return query

    def list_zun_service(self, filters=None, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        query = model_query(models.ZunService)
        if filters:
            query = self._add_zun_service_filters(query, filters)

        return _paginate_query(models.ZunService, limit, marker,
                               sort_key, sort_dir, query)

    def list_zun_service_by_binary(cls, binary):
        query = model_query(models.ZunService)
        query = query.filter_by(binary=binary)
        return _paginate_query(models.ZunService, query=query)

    def pull_image(self, context, values):
        # ensure defaults are present for new containers
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()
        image = models.Image()
        image.update(values)
        try:
            image.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ImageAlreadyExists(tag=values['tag'],
                                               repo=values['repo'])
        return image

    def update_image(self, image_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Image.")
            raise exception.InvalidParameterValue(err=msg)
        return self._do_update_image(image_id, values)

    def _do_update_image(self, image_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Image, session=session)
            query = add_identity_filter(query, image_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ImageNotFound(image=image_id)

            ref.update(values)
        return ref

    def _add_image_filters(self, query, filters):
        if filters is None:
            filters = {}

        filter_names = ['repo', 'project_id', 'user_id', 'size']
        for name in filter_names:
            if name in filters:
                query = query.filter_by(**{name: filters[name]})

        return query

    def list_image(self, context, filters=None, limit=None, marker=None,
                   sort_key=None, sort_dir=None):
        query = model_query(models.Image)
        query = self._add_tenant_filters(context, query)
        query = self._add_image_filters(query, filters)
        return _paginate_query(models.Image, limit, marker, sort_key,
                               sort_dir, query)

    def get_image_by_id(self, context, image_id):
        query = model_query(models.Image)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=image_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ImageNotFound(image=image_id)

    def get_image_by_uuid(self, context, image_uuid):
        query = model_query(models.Image)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=image_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ImageNotFound(image=image_uuid)

    def _add_resource_providers_filters(self, query, filters):
        if filters is None:
            filters = {}

        filter_names = ['name', 'root_provider', 'parent_provider', 'can_host']
        for name in filter_names:
            if name in filters:
                query = query.filter_by(**{name: filters[name]})

        return query

    def list_resource_provider(self, context, filters=None, limit=None,
                               marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.ResourceProvider)
        query = self._add_resource_providers_filters(query, filters)
        return _paginate_query(models.ResourceProvider, limit, marker,
                               sort_key, sort_dir, query)

    def create_resource_provider(self, context, values):
        # ensure defaults are present for new resource providers
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        resource_provider = models.ResourceProvider()
        resource_provider.update(values)
        try:
            resource_provider.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ResourceProviderAlreadyExists(
                field='UUID', value=values['uuid'])
        return resource_provider

    def get_resource_provider(self, context, provider_ident):
        if uuidutils.is_uuid_like(provider_ident):
            return self._get_resource_provider_by_uuid(context, provider_ident)
        else:
            return self._get_resource_provider_by_name(context, provider_ident)

    def _get_resource_provider_by_uuid(self, context, provider_uuid):
        query = model_query(models.ResourceProvider)
        query = query.filter_by(uuid=provider_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ResourceProviderNotFound(
                resource_provider=provider_uuid)

    def _get_resource_provider_by_name(self, context, provider_name):
        query = model_query(models.ResourceProvider)
        query = query.filter_by(name=provider_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ResourceProviderNotFound(
                resource_provider=provider_name)
        except MultipleResultsFound:
            raise exception.Conflict('Multiple resource providers exist with '
                                     'same name. Please use the uuid instead.')

    def destroy_resource_provider(self, context, provider_id):
        session = get_session()
        with session.begin():
            query = model_query(models.ResourceProvider, session=session)
            query = add_identity_filter(query, provider_id)
            count = query.delete()
            if count != 1:
                raise exception.ResourceProviderNotFound(
                    resource_provider=provider_id)

    def update_resource_provider(self, context, provider_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing ResourceProvider.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_resource_provider(provider_id, values)

    def _do_update_resource_provider(self, provider_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ResourceProvider, session=session)
            query = add_identity_filter(query, provider_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ResourceProviderNotFound(
                    resource_provider=provider_id)

            ref.update(values)
        return ref

    def list_resource_class(self, context, limit=None, marker=None,
                            sort_key=None, sort_dir=None):
        query = model_query(models.ResourceClass)
        return _paginate_query(models.ResourceClass, limit, marker,
                               sort_key, sort_dir, query)

    def create_resource_class(self, context, values):
        resource = models.ResourceClass()
        resource.update(values)
        try:
            resource.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ResourceClassAlreadyExists(
                field='name', value=values['name'])
        return resource

    def get_resource_class(self, context, resource_ident):
        if strutils.is_int_like(resource_ident):
            return self._get_resource_class_by_id(context, resource_ident)
        else:
            return self._get_resource_class_by_name(context, resource_ident)

    def _get_resource_class_by_id(self, context, resource_id):
        query = model_query(models.ResourceClass)
        query = query.filter_by(id=resource_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ResourceClassNotFound(
                resource_class=resource_id)

    def _get_resource_class_by_name(self, context, resource_name):
        query = model_query(models.ResourceClass)
        query = query.filter_by(name=resource_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ResourceClassNotFound(resource_class=resource_name)

    def destroy_resource_class(self, context, resource_id):
        session = get_session()
        with session.begin():
            query = model_query(models.ResourceClass, session=session)
            count = query.delete()
            if count != 1:
                raise exception.ResourceClassNotFound(
                    resource_class=str(resource_id))

    def update_resource_class(self, context, resource_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ResourceClass, session=session)
            query = query.filter_by(id=resource_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ResourceClassNotFound(
                    resource_class=resource_id)

            ref.update(values)
        return ref

    def _add_inventories_filters(self, query, filters):
        if filters is None:
            filters = {}

        filter_names = ['resource_provider_id', 'resource_class_id', 'total',
                        'reserved', 'min_unit', 'max_unit', 'step_size',
                        'allocation_ratio', 'is_nested']
        for name in filter_names:
            if name in filters:
                query = query.filter_by(**{name: filters[name]})

        return query

    def list_inventory(self, context, filters=None, limit=None,
                       marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.Inventory)
        query = self._add_inventories_filters(query, filters)
        return _paginate_query(models.Inventory, limit, marker,
                               sort_key, sort_dir, query)

    def create_inventory(self, context, provider_id, values):
        values['resource_provider_id'] = provider_id
        inventory = models.Inventory()
        inventory.update(values)
        try:
            inventory.save()
        except db_exc.DBDuplicateEntry as e:
            fields = {c: values[c] for c in e.columns}
            raise exception.UniqueConstraintViolated(fields=fields)
        return inventory

    def get_inventory(self, context, inventory_ident):
        if strutils.is_int_like(inventory_ident):
            return self._get_inventory_by_id(context, inventory_ident)
        else:
            return self._get_inventory_by_name(context, inventory_ident)

    def _get_inventory_by_id(self, context, inventory_id):
        query = model_query(models.Inventory)
        query = query.filter_by(id=inventory_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.InventoryNotFound(inventory=inventory_id)

    def _get_inventory_by_name(self, context, inventory_name):
        query = model_query(models.Inventory)
        query = query.filter_by(name=inventory_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.InventoryNotFound(inventory=inventory_name)
        except MultipleResultsFound:
            raise exception.Conflict('Multiple inventories exist with same '
                                     'name. Please use the inventory id '
                                     'instead.')

    def destroy_inventory(self, context, inventory_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Inventory, session=session)
            query = query.filter_by(id=inventory_id)
            count = query.delete()
            if count != 1:
                raise exception.InventoryNotFound(inventory=inventory_id)

    def update_inventory(self, context, inventory_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Inventory, session=session)
            query = query.filter_by(id=inventory_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.InventoryNotFound(inventory=inventory_id)

            ref.update(values)
        return ref

    def _add_allocations_filters(self, query, filters):
        if filters is None:
            filters = {}

        filter_names = ['resource_provider_id', 'resource_class_id',
                        'consumer_id', 'used', 'is_nested']
        for name in filter_names:
            if name in filters:
                query = query.filter_by(**{name: filters[name]})

        return query

    def list_allocations(self, context, filters=None, limit=None,
                         marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.Allocation)
        query = self._add_allocations_filters(query, filters)
        return _paginate_query(models.Allocation, limit, marker,
                               sort_key, sort_dir, query)

    def create_allocation(self, context, values):
        allocation = models.Allocation()
        allocation.update(values)
        try:
            allocation.save()
        except db_exc.DBDuplicateEntry as e:
            fields = {c: values[c] for c in e.columns}
            raise exception.UniqueConstraintViolated(fields=fields)
        return allocation

    def get_allocation(self, context, allocation_id):
        query = model_query(models.Allocation)
        query = query.filter_by(id=allocation_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.AllocationNotFound(allocation=allocation_id)

    def destroy_allocation(self, context, allocation_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Allocation, session=session)
            query = query.filter_by(id=allocation_id)
            count = query.delete()
            if count != 1:
                raise exception.AllocationNotFound(allocation=allocation_id)

    def update_allocation(self, context, allocation_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Allocation, session=session)
            query = query.filter_by(id=allocation_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.AllocationNotFound(allocation=allocation_id)

            ref.update(values)
        return ref
