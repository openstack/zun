# Copyright 2021 University of Chicago
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from oslo_log import log as logging
from oslo_middleware import request_id

from zun.common import clients
from zun.common import context as zun_context
from zun.common import exception

LOG = logging.getLogger(__name__)
RESOURCE_GROUP_REGEX = re.compile(r"^device_profile_(.+?)_(\d+)$")

class CyborgClient(object):
    """Client class for updating the scheduler."""

    def __init__(self, context=None, adapter=None):
        """Initialize the report client.

        :param context: Security context
        :param adapter: A prepared keystoneauth1 Adapter for API communication.
                If unspecified, one is created based on config options in the
                [cyborg_client] section.
        """
        self._context = context or zun_context.get_admin_context()
        self._client, self._ks_filter = self._create_client()

    def _create_client(self):
        """Create the HTTP session accessing the cyborg service."""
        client, ks_filter = clients.OpenStackClients(self._context).cyborg()

        # Set accept header on every request to ensure we notify cyborg
        # service of our response body media type preferences.
        client.additional_headers = {'accept': 'application/json'}
        return client, ks_filter

    def get(self, url, version=None, global_request_id=None):
        headers = ({request_id.INBOUND_HEADER: global_request_id}
                   if global_request_id else {})
        return self._client.get(url, endpoint_filter=self._ks_filter,
                                microversion=version, headers=headers,
                                logger=LOG)

    def post(self, url, data, version=None, global_request_id=None):
        headers = ({request_id.INBOUND_HEADER: global_request_id}
                   if global_request_id else {})
        # NOTE(sdague): using json= instead of data= sets the
        # media type to application/json for us.
        return self._client.post(url, endpoint_filter=self._ks_filter,
                                 json=data, microversion=version,
                                 headers=headers, logger=LOG)

    def patch(self, url, data, version=None, global_request_id=None):
        # NOTE(sdague): using json= instead of data= sets the
        # media type to application/json for us.
        kwargs = {'microversion': version,
                  'endpoint_filter': self._ks_filter,
                  'headers': {request_id.INBOUND_HEADER:
                              global_request_id} if global_request_id else {}}
        if data is not None:
            kwargs['json'] = data
        return self._client.patch(url, logger=LOG, **kwargs)

    def delete(self, url, version=None, global_request_id=None):
        headers = ({request_id.INBOUND_HEADER: global_request_id}
                   if global_request_id else {})
        return self._client.delete(url, endpoint_filter=self._ks_filter,
                                   microversion=version, headers=headers,
                                   logger=LOG)

    def get_request_groups(self, device_profiles):
        resp = self.get("/device_profiles")
        if resp.status_code != 200:
            raise exception.DeviceRequestFailed(
                "Failed to fetch device profiles: %(error)s",
                error=resp.text
            )
        request_groups = {}
        all_profiles = resp.json()["device_profiles"]
        LOG.info(all_profiles)
        for dp in all_profiles:
            if dp["name"] not in device_profiles:
                # NOTE: we do not fail here, should we?
                LOG.warning(
                    "Container requested with device profile: %s, yet it was not "
                    "known to Cyborg", dp["name"])
                continue
            for group_id, group in enumerate(dp["groups"]):
                request_groups[f"device_profile_{dp['name']}_{group_id}"] = group
        return request_groups

    def create_and_bind_arqs(self, container, host_state, device_rps):
        arqs = []
        for device_profile_name in device_rps.keys():
            resp = self.post("/accelerator_requests", {
                "device_profile_name": device_profile_name
            })
            if resp.status_code != 201:
                raise exception.DeviceRequestFailed(
                    device_profile=device_profile_name, error=resp.text)
            arqs.extend(resp.json()["arqs"])

        LOG.info("Created ARQs for %s", container.uuid)

        patch = {}
        for arq in arqs:
            dp_name = arq["device_profile_name"]
            dp_group_id = str(arq["device_profile_group_id"])
            device_rp_uuids = device_rps.get(dp_name, {}).get(dp_group_id, [])
            device_rp_uuid = device_rp_uuids[0] if device_rp_uuids else None
            if not device_rp_uuid:
                raise exception.DeviceRequestFailed(
                    "Failed to find device resource provider for group "
                    "%(group_id)s of profile %(device_profile)s from "
                    "allocations", device_profile=dp_name,
                    group_id=dp_group_id
                )
            patch[arq["uuid"]] = [
                {"path": "/instance_uuid", "value": container.uuid,
                 "op": "add"},
                {"path": "/hostname", "value": host_state["host"],
                 "op": "add"},
                {"path": "/device_rp_uuid", "value": device_rp_uuid,
                 "op": "add"},
            ]

        resp = self.patch("/accelerator_requests", patch)
        if resp.status_code != 202:
            raise exception.DeviceRequestFailed(
                "Failed to bind device ARQs for container: %(error)s",
                error=resp.text
            )

        LOG.info("Bound ARQs for %s", container.uuid)

    def get_bound_arqs(self, container):
        resp = self.get("/accelerator_requests")
        if resp.status_code != 200:
            raise exception.DeviceRequestFailed(
                "Failed to bound ARQs: %(error)s",
                error=resp.text
            )
        return [
            arq for arq in resp.json()["arqs"]
            if arq["instance_uuid"] == container.uuid
        ]

    def delete_bound_arqs(self, container):
        resp = self.delete(
            f"/accelerator_requests?instance={container.uuid}")
        if resp.status_code != 204:
            raise exception.DeviceRequestFailed(
                "Failed to delete bound ARQs: %(error)s",
                error=resp.text
            )
