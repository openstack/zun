# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from six.moves.urllib import parse
from tempest import config
from tempest.lib.common import rest_client
from tempest.lib.services.compute import keypairs_client
from tempest import manager

from zun.container.docker import utils as docker_utils
from zun.tests.tempest.api.models import container_model
from zun.tests.tempest.api.models import service_model
from zun.tests.tempest import utils


CONF = config.CONF


class Manager(manager.Manager):

    def __init__(self, credentials=None, service=None):
        super(Manager, self).__init__(credentials=credentials)

        params = {'service': CONF.container_management.catalog_type,
                  'region': CONF.identity.region}
        self.keypairs_client = keypairs_client.KeyPairsClient(
            self.auth_provider, **params)
        self.container_client = ZunClient(self.auth_provider)


class ZunClient(rest_client.RestClient):

    def __init__(self, auth_provider):
        super(ZunClient, self).__init__(
            auth_provider=auth_provider,
            service=CONF.container_management.catalog_type,
            region=CONF.identity.region,
            disable_ssl_certificate_validation=True
        )

    @classmethod
    def deserialize(cls, resp, body, model_type):
        return resp, model_type.from_json(body)

    @classmethod
    def containers_uri(cls, action=None):
        url = "/containers/"
        if action:
            url = "{0}/{1}".format(url, action)
        return url

    @classmethod
    def container_uri(cls, container_id, action=None, params=None):
        """Construct container uri

        """
        url = None
        if action is None:
            url = "{0}/{1}".format(cls.containers_uri(), container_id)
        else:
            url = "{0}/{1}/{2}".format(cls.containers_uri(), container_id,
                                       action)

        if params:
            url = cls.add_params(url, params)

        return url

    @classmethod
    def add_params(cls, url, params):
        """add_params adds dict values (params) to url as query parameters

        :param url: base URL for the request
        :param params: dict with var:val pairs to add as parameters to URL
        :returns: url string
        """
        url_parts = list(parse.urlparse(url))
        query = dict(parse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = parse.urlencode(query)
        return parse.urlunparse(url_parts)

    @classmethod
    def services_uri(cls):
        url = "/services/"
        return url

    def post_container(self, model, **kwargs):
        """Makes POST /container request

        """
        resp, body = self.post(
            self.containers_uri(),
            body=model.to_json(), **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def run_container(self, model, **kwargs):
        resp, body = self.post(
            self.containers_uri(action='run'),
            body=model.to_json(), **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def get_container(self, container_id):
        resp, body = self.get(self.container_uri(container_id))
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def list_containers(self, **kwargs):
        resp, body = self.get(self.containers_uri(), **kwargs)
        return self.deserialize(resp, body,
                                container_model.ContainerCollection)

    def delete_container(self, container_id, params=None, **kwargs):
        return self.delete(
            self.container_uri(container_id, params=params), **kwargs)

    def start_container(self, container_id, **kwargs):
        resp, body = self.post(
            self.container_uri(container_id, action='start'), None, **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def stop_container(self, container_id, **kwargs):
        resp, body = self.post(
            self.container_uri(container_id, action='stop'), None, *kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def pause_container(self, container_id, **kwargs):
        resp, body = self.post(
            self.container_uri(container_id, action='pause'), None, **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def unpause_container(self, container_id, **kwargs):
        resp, body = self.post(
            self.container_uri(container_id, action='unpause'), None, **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def kill_container(self, container_id, **kwargs):
        resp, body = self.post(
            self.container_uri(container_id, action='kill'), None, **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def reboot_container(self, container_id, **kwargs):
        resp, body = self.post(
            self.container_uri(container_id, action='reboot'), None, **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def exec_container(self, container_id, command, **kwargs):
        return self.post(
            self.container_uri(container_id, action='execute'),
            '{"command": "%s"}' % command, **kwargs)

    def logs_container(self, container_id, **kwargs):
        return self.get(
            self.container_uri(container_id, action='logs'), None, **kwargs)

    def list_services(self, **kwargs):
        resp, body = self.get(self.services_uri(), **kwargs)
        return self.deserialize(resp, body,
                                service_model.ServiceCollection)

    def ensure_container_created(self, container_id):
        def container_created():
            _, container = self.get_container(container_id)
            if container.status == 'Creating':
                return False
            else:
                return True

        utils.wait_for_condition(container_created)

    def ensure_container_started(self, container_id):
        def container_started():
            _, container = self.get_container(container_id)
            if container.status == 'Running':
                return True
            else:
                return False

        utils.wait_for_condition(container_started)


class DockerClient(object):

    def get_container(self, container_id):
        with docker_utils.docker_client() as docker:
            for info in docker.list_instances(inspect=True):
                if container_id in info['Name']:
                    return info
            return None
