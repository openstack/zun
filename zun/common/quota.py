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

"""Quotas for resources per project"""

from oslo_log import log as logging
from oslo_utils import importutils

from zun.common import exception
from zun.common import utils
import zun.conf
from zun import objects

LOG = logging.getLogger(__name__)
CONF = zun.conf.CONF


class DbQuotaDriver(object):
    """Driver to perform necessary checks to enforce quotas and obtain
    quota information. The default driver utilizes the local database.
    """

    def get_by_project(self, context, project_id, resource):
        """Get a specify quota by project."""
        return objects.Quota.get(context, project_id, resource)

    def get_by_class(self, context, quota_class, resource):
        """Get a specifiy quota by quota class."""
        return objects.QuotaClass.get(context, quota_class, resource)

    def get_defaults(self, context, resources):
        """Given a list of resource, retrieve the default quotas.
        Use the class quotas named `DEFAULT_QUOTA_CLASS_NAME` as default
        quotas if it exists.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        """
        quotas = {}
        default_quotas = objects.QuotaClass.get_all(context)
        for resource in resources.values():
            quotas[resource.name] = default_quotas.get(resource.name,
                                                       resource.default)

        return quotas

    def get_class_quotas(self, context, resources, quota_class,
                         defaults=True):
        """Given a list of resources, retrieve the quotas for the given
        quota class.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registerd resources.
        :param quota_class: The name of the quota class to return
                            quotas for.
        :param defaults: If True, the default value will be reported
                         if there is no specific value for the resource.
        """
        quotas = {}
        class_quotas = objects.QuotaClass.get_all(context, quota_class)

        for resource in resources.values():
            if defaults or resource.name in class_quotas:
                quotas[resource.name] = class_quotas.get(resource.name,
                                                         resource.default)

        return quotas

    def _process_quotas(self, context, resources, project_id, quotas,
                        quota_class=None, defaults=True,
                        usages=None):
        modified_quotas = {}
        if quota_class:
            class_quotas = objects.QuotaClass.get_all(context,
                                                      quota_class)
        else:
            class_quotas = {}

        default_quotas = self.get_defaults(context, resources)

        for resource in resources.values():
            # Omit default quota class values
            if not defaults and resource.name not in quotas:
                continue

            limit = quotas.get(resource.name, class_quotas.get(
                resource.name, default_quotas[resource.name]))
            modified_quotas[resource.name] = dict(limit=limit)

            # Include usages if desired. This is optional because one
            # internal consumer of this interface wants to access the
            # usages directly from inside a transaction.
            if usages:
                modified_quotas[resource.name].update(
                    in_use=usages.get(resource.name, 0))

        return modified_quotas

    def get_project_quotas(self, context, resources, project_id,
                           quota_class=None, defaults=True,
                           usages=True, project_quotas=None):
        """Given a list of resources, retrieve the quotas for the given
        project.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        :param project_id: The ID of the project to return quotas for.
        :param quota_class: The quota class name.
        :param defaults: If True, the quota class value (or the default value
                         ,if there is no value from the quota class) will
                         be reported if there is no specific value for the
                         resource.
        :param usages: If True, the current counts will be returned.
        :param project_quotas: Quotas dictionary for the specified project.
        """
        project_quotas = project_quotas or objects.Quota.get_all(context,
                                                                 project_id)
        project_usages = {}
        if usages:
            for resource in resources.values():
                project_usages[resource.name] = resource.count(context,
                                                               project_id)
        return self._process_quotas(context, resources, project_id,
                                    project_quotas, quota_class,
                                    defaults=defaults, usages=project_usages)

    def _get_quotas(self, context, resources, keys, project_id=None,
                    project_quotas=None):
        """A helper method which retrieves the quotas for the specific
        resources identified by keys, and which apply to the current
        context.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        :param keys: A list of the desired quotas to retrieve.
        :param project_id: Specify the project_id if current context
                           is admin and admin wants to impact on
                           common user's project.
        :param project_quotas: Quotas dictionary for the specified project.
        """

        # Filter resources
        desired = set(keys)
        sub_resources = {k: v for k, v in resources.items() if k in desired}

        # Make sure we accounted for all of them...
        LOG.debug('Getting quotas for project %(project_id)s. Resources:'
                  '%(keys)s', {'project_id': project_id, 'keys': keys})
        # Grab and return the quotas (without usages)
        quotas = self.get_project_quotas(context, sub_resources,
                                         project_id,
                                         usages=False,
                                         project_quotas=project_quotas)

        return {k: v['limit'] for k, v in quotas.items()}

    def limit_check(self, context, resources, values, project_id=None):
        """Check simple quota limits.

        For limits--those quotas for which there is no usage
        synchronization function--this method checks that a set of
        proposed values are permitted by the limit restriction.

        This method will raise a QuotaResourceUnknown exception if a
        given resource is unknown if it is not a simple limit resource.

        If any of the proposed values is over the defined quota, an
        OverQuota exception will be raised with the sorted list of the
        resources which are too high. Otherwise, the method returns
        nothing.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registerd resources.
        :param values: A dictionary of the values to check against the
                       quota.
        :param project_id: Specify the project_id if current context
                           is admin and admin wants to impact on common
                           user's project.
        """
        _valid_method_call_check_resources(values, 'check', resources)

        # Ensure no value is less than zero
        unders = [key for key, val in values.items() if val < 0]
        if unders:
            raise exception.InvalidQuotaValue(unders=sorted(unders))

        # If project_id is None, then we use the project_id in context
        if project_id is None:
            project_id = context.project_id

        # Get applicable quotas
        project_quotas = objects.Quota.get_all(context, project_id)
        quotas = self._get_quotas(context, resources, values.keys(),
                                  project_id=project_id,
                                  project_quotas=project_quotas)
        # Check the quotas and construct a list of the resources that
        # would be put over limit by the desired values
        overs = [key for key, val in values.items()
                 if quotas[key] >= 0 and utils.is_less_than(quotas[key], val)]

        if overs:
            headroom = {}
            for key in overs:
                headroom[key] = min(
                    val for val in (quotas.get(key), project_quotas.get(key))
                    if val is not None
                )
            raise exception.OverQuota(overs=sorted(overs), quotas=quotas,
                                      usages={}, headroom=headroom)

    def destroy_all_by_project(self, context, project_id):
        """Destroy all quotas associated with a project.

        :param context: The request context, for access checks.
        :param project_id: The ID of the project being deleted.
        """
        objects.Quota.destroy_all_by_project(context, project_id)


class NoopQuotaDriver(object):
    """Driver that turns quotas calls into no-ops and pretends that quotas
    for all resources are unlimited. This can be used if you do not wish to
    have any quota checking.
    """

    def get_by_project(self, context, project_id, resource):
        """Get a specific quota by project."""
        # Unlimited
        return -1

    def get_by_class(self, context, quota_class, resource):
        """Get a specific quota by quota class."""
        # Unlimited
        return -1

    def get_defaults(self, context, resources):
        """Given a list of resources, retrieve the default quotas.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        """
        quotas = {}
        for resource in resources.values():
            quotas[resource.name] = -1
        return quotas

    def get_class_quotas(self, context, resources, quota_class, defaults=True):
        """Given a list resources, retrieve the quotas for the given
        quota class.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registerd resources.
        :param quota_class: The name of the quota class to return
                            quotas for.
        :param defaults: If True, the default value will be reported
                         if there is no specific value for the
                         resource.
        """
        quotas = {}
        for resource in resources.values():
            quotas[resource.name] = -1
        return quotas

    def get_project_quotas(self, context, resources, project_id,
                           quota_class=None, defaults=None,
                           usages=True):
        """Given a list of resources, retrieve the quotas for the given
        project.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        :param project_id: The ID of the project to return quotas for.
        :param quota_class: The name of the quota class to return
                            quotas for.
        :param defaults: If True, the quota class value (or the default value,
                         if there is no value from the quota class) will be
                         reported if there is no specific value for
                         the resource.
        :param usage: If True, the current counts will also be returned.
        """
        quotas = {}
        for resource in resources.values():
            quotas[resource.name] = {}
            quotas[resource.name]['limit'] = -1
            if usages:
                quotas[resource.name]['in_use'] = -1
        return quotas

    def limit_check(self, context, resources, values, project_id=None):
        """Check simple quota limits.

        For limit--those quotas for which there is no usage
        synchronization function--this method checks that a set of
        proposed values are permitted by the limit restriction.

        If any of the proposed values is over the defined quota, an
        OverQuota exception will be raised with the sorted list of
        the resources which are too high. Otherwise, the method returns
        nothing.

        :param context: The request context, for acccess checks.
        :param resources: A dictionary of the registered resources.
        :param values: A dictionary of the values to check against
                       the quota.
        :param project_id: Specify the project_id if current context is
                           admin and the admin wants to impact on
                           common user's project.
        """
        pass

    def destroy_all_by_project(self, context, project_id):
        """Destroy all quotas associated with a project.

        :param context: The request context, for access checks.
        :param project_id: The ID the project being deleted.
        """
        pass


class BaseResource(object):
    """Describe a single resource for quota checking."""

    def __init__(self, name, flag=None):
        """Initalizes a Resource.

        :param name: The name of the resource, i.e., "containers".
        :param flag: The name of the flag or configuration option
                     which specifies the default value of the quota
                     for this resource.
        """
        self.name = name
        self.flag = flag

    def quota(self, driver, context, **kwargs):
        """Given a driver and context, obtains the quota for this
        resource.

        :param driver: A quota driver.
        :param context: The request context.
        :param project_id: The project to obtain the quota value for.
                           If not provided, it is taken from the context.
                           If it is given as None, no project-specific
                           quota will be searched for.
        :param quota_class: The name of the quota class to return
                            quotas for.
        """
        # Get the project ID
        project_id = kwargs.get('project_id', context.project_id)

        # Get the quota class
        quota_class = kwargs.get('quota_class')

        # Look up the quota for the project
        if project_id:
            try:
                return driver.get_by_project(context, project_id, self.name)
            except exception.ProjectQuotaNotFound:
                pass

        # Try for the quota class
        if quota_class:
            try:
                return driver.get_by_class(context, quota_class, self.name)
            except exception.QuotaClassNotFound:
                pass

        return self.default

    @property
    def default(self):
        """Return the default value of the quota."""
        return CONF.quota[self.flag] if self.flag else -1


class AbsoluteResource(BaseResource):
    """Describe a resource that does not correspond to database objects."""
    pass


class CountableResource(BaseResource):
    """Describe a resource where the counts aren't based solely on the
    project ID.
    """

    def __init__(self, name, count, flag=None):
        """Initalizes a CountableResource.

        Countable resources are those resources which directly
        correspond to objects in the database, but for which a count
        by project ID is inappropriate.

        A CountableResource must be constructed with a counting
        function, which will be called to determine the current counts
        of the resource.

        The counting function will be passed the context, along with
        the extra positional and keyword arguments that are passed to
        Quota.count_(). It should return an integer specifying the
        count scoped to a project.

        Note that this counting is not performed a transaction-safe
        manner.

        :param name: The name of the resource, i.e., "containers"
        :param count: A callable which returns the count of the
                      resource. The arguments passed are as described
                      above.
        :param flag: The name of the flag or configuration option
                     which specfies the default value of the quota
                     for this resource.
        """
        super(CountableResource, self).__init__(name, flag=flag)
        self._count = count

    def count(self, context, project_id):
        return self._count(context, project_id)


class QuotaEngine(object):
    """Represent the set of recognized quotas."""

    def __init__(self, quota_driver=None):
        """Initalize a Quota object."""
        self._resources = {}
        self.__driver = quota_driver

    @property
    def _driver(self):
        if self.__driver:
            return self.__driver

        self.__driver = importutils.import_object(CONF.quota.driver)
        return self.__driver

    def register_resource(self, resource):
        """Register a resource"""

        self._resources[resource.name] = resource

    def register_resources(self, resources):
        """Register a list of resources."""

        for resource in resources:
            self.register_resource(resource)

    def get_by_project(self, context, project_id, resource):
        """Get a specific quota by project."""

        return self._driver.get_by_project(context, project_id, resource)

    def get_by_class(self, context, quota_class, resource):
        """Get a specific quota by quota class."""

        return self._driver.get_by_class(context, quota_class, resource)

    def get_defaults(self, context):
        """Retrieve the default quotas.

        :param context: The request context, for access checks.
        """

        return self._driver.get_defaults(context, self._resources)

    def get_class_quotas(self, context, quota_class, defaults=True):
        """Retrieve the quotas for the given quota class.

        :param context: The request context, for access checks.
        :param quota_class: The name of the quota class to return
                            quotas for.
        :param defaults: If True, the default value will be reported
                         if there is no specific value for the resource.
        """

        return self._driver.get_class_quotas(context, self._resources,
                                             quota_class, defaults=defaults)

    def get_project_quotas(self, context, project_id, quota_class=None,
                           defaults=True, usages=True):
        """Retrieve the quotas for the given project.

        :param context: The request context, for access checks.
        :param project_id: The ID of the project to return quotas for.
        :param quota_class: The name of the quota class to return
                            quotas for.
        :param defaults: If True, the quota class value (or the default
                         value, if there is no value from the quota class)
                         will be reported if there is no specific value
                         for the resource.
        :param usages: If True, the current counts will also be returned.
        """

        return self._driver.get_project_quotas(context, self._resources,
                                               project_id,
                                               quota_class=quota_class,
                                               defaults=defaults,
                                               usages=usages)

    def count(self, context, resource, project_id):
        """Count a resource.

        For countable resources, invokes the count() function and
        returns its result. Argument following the context and
        resource are passed directly to the count function declared
        by the resource.

        :param context: The request context, for access check.
        :param resource: The name of the resource, as a string.
        """

        # Get the resource
        res = self._resources.get(resource)
        if not res or not hasattr(res, 'count'):
            raise exception.QuotaResourceUnknown(unknown=[resource])

        return res.count(context, project_id)

    def limit_check(self, context, project_id=None, **values):
        """Check simple quota limits.

        For limits--those quotas for which there is no usage
        synchronization function--this method checks that a set of
        proposed values are permitted by the limit restriction. The
        values to check are given as keyword arguments, where the key
        identifies the specific quota limit to check, and the value
        is the proposed value.

        This method will raise a QuotaResourceUnknown exception if a
        given resource is unknown or if it is not a simple limit resource.

        If any of proposed values is over the defined quota, an OverQuota
        exception will be raised with the sorted list of the resources
        which are too high. Otherwise, the method returns nothing.

        :param context: The rquest context, for access checks.
        :param project_id: Specify the project_id if current context
                           is admin and admin wants to impact on
                           common user's project.
        """

        return self._driver.limit_check(context, self._resources, values,
                                        project_id=project_id)

    def destroy_all_by_project(self, context, project_id):
        """Destroy all quotas, usages associated with a project.

        :param context: The request context, for access checks.
        :param project_id: The ID of the project being deleted.
        """

        self._driver.destroy_all_by_project(context, project_id)

    @property
    def resources(self):
        if isinstance(self._driver, NoopQuotaDriver):
            return -1
        return sorted(self._resources.keys())


def _containers_count(context, project_id):
    return objects.Container.get_count(context, project_id, flag='containers')


def _cpu_count(context, project_id):
    return round(objects.Container.get_count(
        context, project_id, flag='cpu'), 3)


def _disk_count(context, project_id):
    return objects.Container.get_count(context, project_id, flag='disk')


def _memory_count(context, project_id):
    return objects.Container.get_count(context, project_id, flag='memory')


QUOTAS = QuotaEngine()


resources = [
    CountableResource('containers', _containers_count, flag='containers'),
    CountableResource('memory', _memory_count, flag='memory'),
    CountableResource('disk', _disk_count, flag='disk'),
    CountableResource('cpu', _cpu_count, flag='cpu')
]


QUOTAS.register_resources(resources)


def _valid_method_call_check_resource(name, method, resources):
    if name not in resources:
        raise exception.InvalidQuotaMethodUsage(method=method, res=name)


def _valid_method_call_check_resources(resource_values, method, resources):
    """A method to check whether the resource can use the quota method.

    :param resource_values: Dict containing the resource names and values.
    :param method: The quota method to check.
    :param resources: Dict containing Resource objects to validate against.
    """

    for name in resource_values.keys():
        _valid_method_call_check_resource(name, method, resources)
