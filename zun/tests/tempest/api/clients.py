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

from zun.tests.tempest.api.models import container_model


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
    def add_filters(cls, url, filters):
        """add_filters adds dict values (filters) to url as query parameters

        :param url: base URL for the request
        :param filters: dict with var:val pairs to add as parameters to URL
        :returns: url string
        """
        return url + "?" + parse(filters)

    @classmethod
    def containers_uri(cls, filters=None):
        url = "/containers/"
        if filters:
            url = cls.add_filters(url, filters)
        return url

    @classmethod
    def container_uri(cls, container_id):
        """Construct container uri

        """
        return "{0}/{1}".format(cls.containers_uri(), container_id)

    def post_container(self, model, **kwargs):
        """Makes POST /container request

        """
        resp, body = self.post(
            self.containers_uri(),
            body=model.to_json(), **kwargs)
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def get_container(self, container_id):
        resp, body = self.get(self.container_uri(container_id))
        return self.deserialize(resp, body, container_model.ContainerEntity)

    def list_containers(self, filters=None, **kwargs):
        resp, body = self.get(self.containers_uri(filters), **kwargs)
        return self.deserialize(resp, body,
                                container_model.ContainerCollection)

    def delete_container(self, container_id, **kwargs):
        self.delete(self.container_uri(container_id), **kwargs)
