#    Copyright 2016 IBM Corp.
#
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


class Manager(object):
    '''Manages the running containers.'''

    def __init__(self):
        super(Manager, self).__init__()

    def container_create(self, context, container):
        pass

    def container_delete(self, context, container_uuid):
        pass

    def container_show(self, context, container_uuid):
        pass

    def container_reboot(self, context, container_uuid):
        pass

    def container_stop(self, context, container_uuid):
        pass

    def container_start(self, context, container_uuid):
        pass

    def container_pause(self, context, container_uuid):
        pass

    def container_unpause(self, context, container_uuid):
        pass

    def container_logs(self, context, container_uuid):
        pass

    def container_exec(self, context, container_uuid, command):
        pass
