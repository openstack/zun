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

from zun.tests.tempest.api.common import base_model


class ContainerData(base_model.BaseModel):
    """Data that encapsulates container attributes"""
    pass


class ContainerEntity(base_model.EntityModel):
    """Entity Model that represents a single instance of ContainerData"""
    ENTITY_NAME = 'container'
    MODEL_TYPE = ContainerData


class ContainerCollection(base_model.CollectionModel):
    """Collection Model that represents a list of ContainerData objects"""
    COLLECTION_NAME = 'containerlists'
    MODEL_TYPE = ContainerData


class ContainerPatchData(base_model.BaseModel):
    """Data that encapsulates container update attributes"""
    pass


class ContainerPatchEntity(base_model.EntityModel):
    """Entity Model that represents a single instance of ContainerPatchData"""
    ENTITY_NAME = 'containerpatch'
    MODEL_TYPE = ContainerPatchData
