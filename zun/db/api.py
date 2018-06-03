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

from zun.common import profiler
import zun.conf

"""Add the database backend mapping here"""

CONF = zun.conf.CONF
_BACKEND_MAPPING = {'sqlalchemy': 'zun.db.sqlalchemy.api',
                    'etcd': 'zun.db.etcd.api'}
IMPL = db_api.DBAPI.from_config(CONF,
                                backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


@profiler.trace("db")
def _get_dbdriver_instance():
    """Return a DB API instance."""
    return IMPL


@profiler.trace("db")
def list_containers(context, filters=None, limit=None, marker=None,
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
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_containers(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_container(context, values):
    """Create a new container.

    :param context: The security context
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


@profiler.trace("db")
def get_container_by_uuid(context, container_uuid):
    """Return a container.

    :param context: The security context
    :param container_uuid: The uuid of a container.
    :returns: A container.
    """
    return _get_dbdriver_instance().get_container_by_uuid(
        context, container_uuid)


@profiler.trace("db")
def get_container_by_name(context, container_name):
    """Return a container.

    :param context: The security context
    :param container_name: The name of a container.
    :returns: A container.
    """
    return _get_dbdriver_instance().get_container_by_name(
        context, container_name)


@profiler.trace("db")
def destroy_container(context, container_id):
    """Destroy a container and all associated interfaces.

    :param context: Request context
    :param container_id: The id or uuid of a container.
    """
    return _get_dbdriver_instance().destroy_container(context, container_id)


@profiler.trace("db")
def update_container(context, container_id, values):
    """Update properties of a container.

    :param context: Request context
    :param container_id: The id or uuid of a container.
    :param values: The properties to be updated
    :returns: A container.
    :raises: ContainerNotFound
    """
    return _get_dbdriver_instance().update_container(
        context, container_id, values)


@profiler.trace("db")
def list_volume_mappings(context, filters=None, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
    """List matching volume mappings.

    Return a list of the specified columns for all volume mappings that match
    the specified filters.

    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of containers to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_volume_mappings(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_volume_mapping(context, values):
    """Create a volume mapping.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the volume mapping.
    :returns: A volume mapping.
    """
    return _get_dbdriver_instance().create_volume_mapping(context, values)


@profiler.trace("db")
def get_volume_mapping_by_uuid(context, vm_uuid):
    """Return a volume mapping.

    :param context: The security context
    :param vm_uuid: The uuid of a volume mapping.
    :returns: A volume mapping.
    """
    return _get_dbdriver_instance().get_volume_mapping_by_uuid(
        context, vm_uuid)


@profiler.trace("db")
def destroy_volume_mapping(context, vm_id):
    """Destroy a volume mapping.

    :param context: Request context
    :param vm_id: The id or uuid of a volume mapping.
    """
    return _get_dbdriver_instance().destroy_volume_mapping(context, vm_id)


@profiler.trace("db")
def update_volume_mapping(context, vm_id, values):
    """Update properties of a volume mapping.

    :param context: Request context
    :param vm_id: The id or uuid of a volume mapping.
    :param values: The properties to be updated
    :returns: A volume mapping.
    :raises: VolumeMappingNotFound
    """
    return _get_dbdriver_instance().update_volume_mapping(
        context, vm_id, values)


@profiler.trace("db")
def destroy_zun_service(host, binary):
    """Destroys a zun_service record.

    :param host: The host on which the service resides.
    :param binary: The binary file name of the service.
    :returns: A zun service record.
    """
    return _get_dbdriver_instance().destroy_zun_service(host, binary)


@profiler.trace("db")
def update_zun_service(host, binary, values):
    """Update properties of a zun_service.

    :param host: The host on which the service resides.
    :param binary: The binary file name of the service.
    :param values: The attributes to be updated.
    :returns: A zun service record.
    """
    return _get_dbdriver_instance().update_zun_service(host, binary, values)


@profiler.trace("db")
def get_zun_service(context, host, binary):
    """Return a zun_service record.

    :param context: The security context
    :param host: The host where the binary is located.
    :param binary: The name of the binary.
    :returns: A zun_service record.
    """
    return _get_dbdriver_instance().get_zun_service(host, binary)


@profiler.trace("db")
def create_zun_service(values):
    """Create a new zun_service record.

    :param values: A dict containing several items used to identify
                   and define the zun_service record.
    :returns: A zun_service record.
    """
    return _get_dbdriver_instance().create_zun_service(values)


@profiler.trace("db")
def list_zun_services(context, filters=None, limit=None,
                      marker=None, sort_key=None, sort_dir=None):
    """Get matching zun_service records.

    Return a list of the specified columns for all zun_services
    those match the specified filters.

    :param context: The security context
    :param filters: Filters disbaled services. Defaults to None.
    :param limit: Maximum number of zun_services to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_zun_services(
        filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def list_zun_services_by_binary(context, binary):
    """List matching zun services.

    Return a list of the specified binary.

    :param context: The security context
    :param binary: The name of the binary.
    :returns: A list of tuples of the specified binary.
    """
    return _get_dbdriver_instance().list_zun_services_by_binary(binary)


@profiler.trace("db")
def destroy_image(context, image_uuid):
    """Destroy a image"""
    return _get_dbdriver_instance().destroy_image(context, image_uuid)


@profiler.trace("db")
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


@profiler.trace("db")
def update_image(image_id, values):
    """Update properties of an image.

    :param image_id: The id or uuid of an image.
    :param values: The properties to be updated.
    :returns: An Image.
    :raises: ImageNotFound
    """
    return _get_dbdriver_instance().update_image(image_id, values)


@profiler.trace("db")
def list_images(context, filters=None,
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
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_images(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def get_image_by_id(context, image_id):
    """Return an image.

    :param context: The security context
    :param image_id: The id of an image.
    :returns: An image.
    """
    return _get_dbdriver_instance().get_image_by_id(context, image_id)


@profiler.trace("db")
def get_image_by_uuid(context, image_uuid):
    """Return an image.

    :param context: The security context
    :param image_uuid: The uuid of an image.
    :returns: An image.
    """
    return _get_dbdriver_instance().get_image_by_uuid(context, image_uuid)


@profiler.trace("db")
def list_resource_providers(context, filters=None, limit=None, marker=None,
                            sort_key=None, sort_dir=None):
    """Get matching resource providers.

    Return a list of the specified columns for all resource providers that
    match the specified filters.

    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of resource providers to return.
    :param marker: the last item of the previous page; we
                    return the next
    :param sort_key: Attribute by which results should be sorted.
                    (asc, desc)
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_resource_providers(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_resource_provider(context, values):
    """Create a new resource provider.

    :param context: The security context
    :param values: A dict containing several items used to identify and
                   track the resource provider, and several dicts which are
                   passed into the Drivers when managing this resource
                   provider.
    :returns: A resource provider.
    """
    return _get_dbdriver_instance().create_resource_provider(context, values)


@profiler.trace("db")
def get_resource_provider(context, provider_ident):
    """Return a resource provider.

    :param context: The security context
    :param provider_ident: The uuid or name of a resource provider.
    :returns: A resource provider.
    """
    return _get_dbdriver_instance().get_resource_provider(
        context, provider_ident)


@profiler.trace("db")
def destroy_resource_provider(context, provider_id):
    """Destroy a resource provider and all associated interfaces.

    :param context: Request context
    :param provider_id: The id or uuid of a resource provider.
    """
    return _get_dbdriver_instance().destroy_resource_provider(
        context, provider_id)


@profiler.trace("db")
def update_resource_provider(context, provider_id, values):
    """Update properties of a resource provider.

    :param context: Request context
    :param provider_id: The id or uuid of a resource provider.
    :param values: The properties to be updated
    :returns: A resource provider.
    :raises: ResourceProviderNotFound
    """
    return _get_dbdriver_instance().update_resource_provider(
        context, provider_id, values)


@profiler.trace("db")
def list_resource_classes(context, limit=None, marker=None, sort_key=None,
                          sort_dir=None):
    """Get matching resource classes.

    Return a list of the specified columns for all resource classes.

    :param context: The security context
    :param limit: Maximum number of resource classes to return.
    :param marker: the last item of the previous page; we
                    return the next
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_resource_classes(
        context, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_resource_class(context, values):
    """Create a new resource class.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the resource class, and several dicts which are
                   passed into the Drivers when managing this resource class.
    :returns: A resource class.
    """
    return _get_dbdriver_instance().create_resource_class(context, values)


@profiler.trace("db")
def get_resource_class(context, resource_ident):
    """Return a resource class.

    :param context: The security context
    :param resource_ident: The uuid or name of a resource class.
    :returns: A resource class.
    """
    return _get_dbdriver_instance().get_resource_class(
        context, resource_ident)


@profiler.trace("db")
def destroy_resource_class(context, resource_uuid):
    """Destroy a resource class and all associated interfaces.

    :param context: Request context
    :param resource_uuid: The uuid of a resource class.
    """
    return _get_dbdriver_instance().destroy_resource_class(
        context, resource_uuid)


@profiler.trace("db")
def update_resource_class(context, resource_uuid, values):
    """Update properties of a resource class.

    :param context: Request context
    :param resource_uuid: The uuid of a resource class.
    :param values: The properties to be updated
    :returns: A resource class.
    :raises: ResourceClassNotFound
    """
    return _get_dbdriver_instance().update_resource_class(
        context, resource_uuid, values)


@profiler.trace("db")
def list_inventories(context, filters=None, limit=None, marker=None,
                     sort_key=None, sort_dir=None):
    """List matching inventories.

    Return a list of the specified columns for all inventories that match
    the specified filters.

    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of inventories to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_inventories(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_inventory(context, provider_id, values):
    """Create a new inventory.

    :param context: The security context
    :param provider_id: The id of a resource provider.
    :param values: A dict containing several items used to identify
                   and track the inventory, and several dicts which are
                   passed into the Drivers when managing this inventory.
    :returns: An inventory.
    """
    return _get_dbdriver_instance().create_inventory(
        context, provider_id, values)


@profiler.trace("db")
def get_inventory(context, inventory_ident):
    """Return a inventory.

    :param context: The security context
    :param inventory_ident: The id or name of an inventory.
    :returns: An inventory.
    """
    return _get_dbdriver_instance().get_inventory(
        context, inventory_ident)


@profiler.trace("db")
def destroy_inventory(context, inventory_id):
    """Destroy an inventory and all associated interfaces.

    :param context: Request context
    :param inventory_id: The id of a inventory.
    """
    return _get_dbdriver_instance().destroy_inventory(context, inventory_id)


@profiler.trace("db")
def update_inventory(context, inventory_id, values):
    """Update properties of an inventory.

    :param context: Request context
    :param inventory_id: The id of an inventory.
    :param values: The properties to be updated
    :returns: An inventory.
    :raises: InventoryNotFound
    """
    return _get_dbdriver_instance().update_inventory(
        context, inventory_id, values)


@profiler.trace("db")
def list_allocations(context, filters=None, limit=None, marker=None,
                     sort_key=None, sort_dir=None):
    """List matching allocations.

    Return a list of the specified columns for all allocations that match
    the specified filters.

    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of allocations to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_allocations(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_allocation(context, values):
    """Create a new allocation.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the allocation, and several dicts which are
                   passed into the Drivers when managing this allocation.
    :returns: An allocation.
    """
    return _get_dbdriver_instance().create_allocation(context, values)


@profiler.trace("db")
def get_allocation(context, allocation_id):
    """Return an allocation.

    :param context: The security context
    :param allocation_id: The id of an allocation.
    :returns: An allocation.
    """
    return _get_dbdriver_instance().get_allocation(context, allocation_id)


@profiler.trace("db")
def destroy_allocation(context, allocation_id):
    """Destroy an allocation and all associated interfaces.

    :param context: Request context
    :param allocation_id: The id of an allocation.
    """
    return _get_dbdriver_instance().destroy_allocation(context, allocation_id)


@profiler.trace("db")
def update_allocation(context, allocation_id, values):
    """Update properties of an allocation.

    :param context: Request context
    :param allocation_id: The id of an allocation.
    :param values: The properties to be updated
    :returns: An allocation.
    :raises: AllocationNotFound
    """
    return _get_dbdriver_instance().update_allocation(
        context, allocation_id, values)


@profiler.trace("db")
def list_compute_nodes(context, filters=None, limit=None, marker=None,
                       sort_key=None, sort_dir=None):
    """List matching compute nodes.

    Return a list of the specified columns for all compute nodes that match
    the specified filters.

    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of compute nodes to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_compute_nodes(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_compute_node(context, values):
    """Create a new compute node.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the compute node, and several dicts which are
                   passed into the Drivers when managing this compute node.
    :returns: A compute node.
    """
    return _get_dbdriver_instance().create_compute_node(context, values)


@profiler.trace("db")
def get_compute_node(context, node_uuid):
    """Return a compute node.

    :param context: The security context
    :param node_uuid: The uuid of a compute node.
    :returns: A compute node.
    """
    return _get_dbdriver_instance().get_compute_node(context, node_uuid)


@profiler.trace("db")
def get_compute_node_by_hostname(context, hostname):
    """Return a compute node.

    :param context: The security context
    :param hostname: The hostname of a compute node.
    :returns: A compute node.
    """
    return _get_dbdriver_instance().get_compute_node_by_hostname(
        context, hostname)


@profiler.trace("db")
def destroy_compute_node(context, node_uuid):
    """Destroy a compute node and all associated interfaces.

    :param context: Request context
    :param node_uuid: The uuid of a compute node.
    """
    return _get_dbdriver_instance().destroy_compute_node(context, node_uuid)


@profiler.trace("db")
def update_compute_node(context, node_uuid, values):
    """Update properties of a compute node.

    :param context: Request context
    :param node_uuid: The uuid of a compute node.
    :param values: The properties to be updated
    :returns: A compute node.
    :raises: ComputeNodeNotFound
    """
    return _get_dbdriver_instance().update_compute_node(
        context, node_uuid, values)


@profiler.trace("db")
def list_capsules(context, filters=None, limit=None, marker=None,
                  sort_key=None, sort_dir=None):
    """List matching capsules.

    Return a list of the specified columns for all capsules that match
    the specified filters.

    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of capsules to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of tuples of the specified columns.
    """
    return _get_dbdriver_instance().list_capsules(
        context, filters, limit, marker, sort_key, sort_dir)


@profiler.trace("db")
def create_capsule(context, values):
    """Create a new capsule.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the container, and several dicts which are
                   passed into the Drivers when managing this container.
                   For example:
                   ::

                    {
                     'uuid': uuidutils.generate_uuid(),
                     'restart_policy': 'always',
                     'project_id': '***'
                    }
    :returns: A capsule.
    """
    return _get_dbdriver_instance().create_capsule(context, values)


@profiler.trace("db")
def get_capsule_by_uuid(context, capsule_uuid):
    """Return a capsule.

    :param context: The security context
    :param capsule_uuid: The uuid of a capsule.
    :returns: A capsule.
    """
    return _get_dbdriver_instance().get_capsule_by_uuid(
        context, capsule_uuid)


@profiler.trace("db")
def get_capsule_by_meta_name(context, capsule_name):
    """Return a capsule.

    :param context: The security context
    :param capsule_name: The meta_name of a capsule.
    :returns: A capsule.
    """
    return _get_dbdriver_instance().get_capsule_by_meta_name(
        context, capsule_name)


@profiler.trace("db")
def destroy_capsule(context, capsule_id):
    """Destroy a capsule and all associated interfaces.

    :param context: Request context
    :param capsule_id: The id or uuid of a capsule.
    """
    return _get_dbdriver_instance().destroy_capsule(context, capsule_id)


@profiler.trace("db")
def update_capsule(context, capsule_id, values):
    """Update properties of a capsule.

    :param context: Request context
    :param capsule_id: The id or uuid of a capsule.
    :param values: The properties to be updated
    :returns: A capsule.
    :raises: CapsuleNotFound
    """
    return _get_dbdriver_instance().update_capsule(
        context, capsule_id, values)


@profiler.trace("db")
def get_pci_device_by_addr(node_id, dev_addr):
    """Get PCI device by address."""
    return _get_dbdriver_instance().get_pci_device_by_addr(node_id, dev_addr)


@profiler.trace("db")
def get_pci_device_by_id(id):
    """Get PCI device by id."""
    return _get_dbdriver_instance().get_pci_device_by_id(id)


@profiler.trace("db")
def get_all_pci_device_by_node(node_id):
    """Get all PCI devices for one host."""
    return _get_dbdriver_instance().get_all_pci_device_by_node(node_id)


@profiler.trace("db")
def get_all_pci_device_by_container_uuid(container_uuid):
    """Get PCI devices allocated to container."""
    return _get_dbdriver_instance().get_all_pci_device_by_container_uuid(
        container_uuid)


@profiler.trace("db")
def get_all_pci_device_by_parent_addr(node_id, parent_addr):
    """Get all PCI devices by parent address."""
    return _get_dbdriver_instance().get_all_pci_device_by_parent_addr(
        node_id, parent_addr)


@profiler.trace("db")
def destroy_pci_device(node_id, address):
    """Delete a PCI device record."""
    return _get_dbdriver_instance().destroy_pci_device(node_id, address)


@profiler.trace("db")
def update_pci_device(node_id, address, value):
    """Update a pci device."""
    return _get_dbdriver_instance().update_pci_device(node_id, address, value)


@profiler.trace("db")
def action_start(context, values):
    """Start an action for an container."""
    return _get_dbdriver_instance().action_start(context, values)


@profiler.trace("db")
def actions_get(context, uuid):
    """Get all container actions for the provided container."""
    return _get_dbdriver_instance().actions_get(context, uuid)


@profiler.trace("db")
def action_get_by_request_id(context, uuid, request_id):
    """Get the action by request_id and given container."""
    return _get_dbdriver_instance().action_get_by_request_id(context, uuid,
                                                             request_id)


@profiler.trace("db")
def action_event_start(context, values):
    """Start an event on an container action."""
    return _get_dbdriver_instance().action_event_start(context, values)


@profiler.trace("db")
def action_event_finish(context, values):
    """Finish an event on an container action."""
    return _get_dbdriver_instance().action_event_finish(context, values)


@profiler.trace("db")
def action_events_get(context, action_id):
    """Get the events by action id."""
    return _get_dbdriver_instance().action_events_get(context, action_id)


@profiler.trace("db")
def quota_create(context, project_id, resource, limit):
    """Create a quota for the given project and resource"""
    return _get_dbdriver_instance().quota_create(context, project_id,
                                                 resource, limit)


@profiler.trace("db")
def quota_get(context, project_id, resource):
    """Retrieve a quota or raise if it does not exist"""
    return _get_dbdriver_instance().quota_get(context, project_id,
                                              resource)


@profiler.trace("db")
def quota_get_all_by_project(context, project_id):
    """Retrieve all quotas associated with a given project"""
    return _get_dbdriver_instance().quota_get_all_by_project(context,
                                                             project_id)


@profiler.trace("db")
def quota_update(context, project_id, resource, limit):
    """Update a quota or raise if it does not exist"""
    return _get_dbdriver_instance().quota_update(context, project_id,
                                                 resource, limit)


@profiler.trace("db")
def quota_destroy(context, project_id, resource):
    """Destroy resource quota associated with a given project"""
    return _get_dbdriver_instance().quota_destroy(context, project_id,
                                                  resource)


@profiler.trace("db")
def quota_destroy_all_by_project(context, project_id, resource):
    """Destroy all resource associated with a given project."""
    return _get_dbdriver_instance().quota_destroy_all_by_project(context,
                                                                 project_id)


@profiler.trace("db")
def quota_class_create(context, class_name, resource, limit):
    """Create a quota class for the given name and resource"""
    return _get_dbdriver_instance().quota_class_create(context, class_name,
                                                       resource, limit)


@profiler.trace("db")
def quota_class_get(context, class_name, resource):
    """Retrieve a quota class or raise if it does not exist"""
    return _get_dbdriver_instance().quota_class_get(context, class_name,
                                                    resource)


@profiler.trace("db")
def quota_class_get_default(context):
    """Retrieve all default quota"""
    return _get_dbdriver_instance().quota_class_get_default(context)


@profiler.trace("db")
def quota_class_get_all_by_name(context, class_name):
    """Retrieve all quotas associated with a given quota class"""
    return _get_dbdriver_instance().quota_class_get_all_by_name(
        context, class_name)


@profiler.trace("db")
def quota_class_update(context, class_name, resource, limit):
    """Update a quota class or raise if it does not exist"""
    return _get_dbdriver_instance().quota_class_update(context, class_name,
                                                       resource, limit)


def quota_usage_get_all_by_project(context, project_id):
    """Retrieve all usage associated with a given resource."""
    return _get_dbdriver_instance().quota_usage_get_all_by_project(context,
                                                                   project_id)


@profiler.trace("db")
def create_network(context, values):
    """Create a new network.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the network, and several dicts which are
                   passed
                   into the Drivers when managing this network. For
                   example:
                   ::
                    {
                     'uuid': uuidutils.generate_uuid(),
                     'name': 'example',
                     'type': 'virt'
                    }
    :returns: A network.
    """
    return _get_dbdriver_instance().create_network(context, values)


@profiler.trace("db")
def get_network_by_uuid(context, network_uuid):
    """Return a network.

    :param context: The security context
    :param network_uuid: The uuid of a network.
    :returns: A network.
    """
    return _get_dbdriver_instance().get_network_by_uuid(context, network_uuid)


@profiler.trace("db")
def update_network(context, uuid, values):
    """Update properties of a network.

    :param context: Request context
    :param uuid: The id or uuid of a network.
    :param values: The properties to be updated
    :returns: A network.
    """
    return _get_dbdriver_instance().update_network(
        context, uuid, values)


@profiler.trace("db")
def create_exec_instance(context, values):
    """Create a new exec instance.

    :param context: The security context
    :param values: A dict containing several items used to identify
                   and track the exec instance, and several dicts which are
                   passed into the Drivers when managing this exec instance.
    :returns: An exec instance.
    """
    return _get_dbdriver_instance().create_exec_instance(context, values)


@profiler.trace("db")
def list_exec_instances(context, filters=None, limit=None, marker=None,
                        sort_key=None, sort_dir=None):
    """List matching exec instances.

    Return a list exec instances that match the specified filters.

    :param context: The security context
    :param filters: Filters to apply. Defaults to None.
    :param limit: Maximum number of containers to return.
    :param marker: the last item of the previous page; we return the next
                   result set.
    :param sort_key: Attribute by which results should be sorted.
    :param sort_dir: Direction in which results should be sorted.
                     (asc, desc)
    :returns: A list of exec instances.
    """
    return _get_dbdriver_instance().list_exec_instances(
        context, filters, limit, marker, sort_key, sort_dir)
