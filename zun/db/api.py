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
Base API for Database
"""

from oslo_db import api as db_api

from zun.common import exception
from zun.common.i18n import _
import zun.conf

"""Add the database backend mapping here"""

CONF = zun.conf.CONF
_BACKEND_MAPPING = {'sqlalchemy': 'zun.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(CONF,
                                backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def _get_dbdriver_instance():
    """Return a DB API instance."""
    if CONF.db_type == 'sql':
        return IMPL
    elif CONF.db_type == 'etcd':
        import zun.db.etcd.api as etcd_api
        return etcd_api.get_connection()
    else:
        raise exception.ConfigInvalid(
            _("db_type value of %s is invalid, "
              "must be sql or etcd") % CONF.db_type)


def list_container(context, filters=None, limit=None, marker=None,
                   sort_key=None, sort_dir=None):
    """List matching containers.

    Return a list of the specified columns for all containers that match
    the specified filters.
    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of containers to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_container(
        context, filters, limit, marker, sort_key, sort_dir)


def create_container(context, values):
    """Create a new container.

    :param values: A dict containing several items used to identify
                   and track the container, and several dicts which are
                   passed
                   into the Drivers when managing this container. For
                   example:
                   ::
                    {
                     'uuid': uuidutils.generate_uuid(),
                     'name': 'example',
                     'type': 'virt'
                    }
    :returns: A container.
    """
    return _get_dbdriver_instance().create_container(context, values)


def get_container_by_uuid(context, container_uuid):
    """Return a container.

    :param context: The security context
    :param container_uuid: The uuid of a container.
    :returns: A container.
    """
    return _get_dbdriver_instance().get_container_by_uuid(
        context, container_uuid)


def get_container_by_name(context, container_name):
    """Return a container.

    :param context: The security context
    :param container_name: The name of a container.
    :returns: A container.
    """
    return _get_dbdriver_instance().get_container_by_name(
        context, container_name)


def destroy_container(context, container_id):
    """Destroy a container and all associated interfaces.

    :param context: Request context
    :param container_id: The id or uuid of a container.
    """
    return _get_dbdriver_instance().destroy_container(context, container_id)


def update_container(context, container_id, values):
    """Update properties of a container.

    :context: Request context
    :param container_id: The id or uuid of a container.
    :values: The properties to be updated
    :returns: A container.
    :raises: ContainerNotFound
    """
    return _get_dbdriver_instance().update_container(
        context, container_id, values)


def destroy_zun_service(host, binary):
    """Destroys a zun_service record.

    :param host: The host on which the service resides.
    :param binary: The binary file name of the service.
    :returns: A zun service record.
    """
    return _get_dbdriver_instance().destroy_zun_service(host, binary)


def update_zun_service(host, binary, values):
    """Update properties of a zun_service.

    :param host: The host on which the service resides.
    :param binary: The binary file name of the service.
    :param values: The attributes to be updated.
    :returns: A zun service record.
    """
    return _get_dbdriver_instance().update_zun_service(host, binary, values)


def get_zun_service(context, host, binary):
    """Return a zun_service record.

    :param context: The security context
    :param host: The host where the binary is located.
    :param binary: The name of the binary.
    :returns: A zun_service record.
    """
    return _get_dbdriver_instance().get_zun_service(host, binary)


def create_zun_service(values):
    """Create a new zun_service record.

    :param values: A dict containing several items used to identify
                   and define the zun_service record.
    :returns: A zun_service record.
    """
    return _get_dbdriver_instance().create_zun_service(values)


def list_zun_service(context, filters=None, limit=None,
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
    return _get_dbdriver_instance().list_zun_service(
        filters, limit, marker, sort_key, sort_dir)


def list_zun_service_by_binary(context, binary):
    """List matching zun services.

    Return a list of the specified binary.
    :param context: The security context
    :param binary: The name of the binary.
    :returns: A list of tuples of the specified binary.
    """
    return _get_dbdriver_instance().list_zun_service_by_binary(binary)


def pull_image(context, values):
    """Create a new image.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the image, and several dicts which are
                   passed
                   into the Drivers when managing this image. For
                   example:
                   ::
                    {
                     'uuid': uuidutils.generate_uuid(),
                     'repo': 'hello-world',
                     'tag': 'latest'
                    }
    :returns: An image.
    """
    return _get_dbdriver_instance().pull_image(context, values)


def update_image(image_id, values):
    """Update properties of an image.

    :param container_id: The id or uuid of an image.
    :returns: An Image.
    :raises: ImageNotFound
    """
    return _get_dbdriver_instance().update_image(image_id, values)


def list_image(context, filters=None,
               limit=None, marker=None,
               sort_key=None, sort_dir=None):
    """Get matching images.

    Return a list of the specified columns for all images that
    match the specified filters.
    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of images to return.
    :param marker: the last item of the previous page; we
                    return the next
    :param sort_key: Attribute by which results should be sorted.
                    (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_image(context, filters, limit, marker,
                                               sort_key, sort_dir)


def get_image_by_id(context, image_id):
    """Return an image.

    :param context: The security context
    :param image_id: The id of an image.
    :returns: An image.
    """
    return _get_dbdriver_instance().get_image_by_id(context, image_id)


def get_image_by_uuid(context, image_uuid):
    """Return an image.

    :param context: The security context
    :param image_uuid: The uuid of an image.
    :returns: An image.
    """
    return _get_dbdriver_instance().get_image_by_uuid(context, image_uuid)
