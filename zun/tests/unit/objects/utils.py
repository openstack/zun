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
"""Zun object test utilities."""


from zun import objects
from zun.tests.unit.db import utils as db_utils


def create_test_container(context, **kwargs):
    """Create and return a test container object.

    Create a container in the DB and return a container object with
    appropriate attributes.
    """
    container = get_test_container(context, **kwargs)
    container.create(context)
    return container


def get_test_container(context, **kwargs):
    """Return a test container object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_container = db_utils.get_test_container(**kwargs)
    container = objects.Container(context)
    for key in db_container:
        setattr(container, key, db_container[key])
    return container
