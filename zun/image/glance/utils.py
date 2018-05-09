# Copyright 2016 Intel.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from glanceclient.common import exceptions as glance_exceptions
from oslo_utils import uuidutils

from zun.common import clients
from zun.common import exception

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def create_glanceclient(context):
    """Creates glance client object.

        :param context: context to create client object
        :returns: Glance client object
    """
    osc = clients.OpenStackClients(context)
    return osc.glance()


def find_image(context, image_ident, tag):
    matches = find_images(context, image_ident, tag, exact_match=True)
    LOG.debug('Found matches %s ', matches)
    if len(matches) == 0:
        raise exception.ImageNotFound(image=image_ident)
    if len(matches) > 1:
        msg = ("Multiple images exist with same name "
               "%(image_ident)s. Please use the image id "
               "instead.") % {'image_ident': image_ident}
        raise exception.Conflict(msg)
    return matches[0]


def find_images(context, image_ident, tag, exact_match):
    glance = create_glanceclient(context)
    if uuidutils.is_uuid_like(image_ident):
        images = []
        try:
            image = glance.images.get(image_ident)
            if image.container_format == 'docker':
                images.append(image)
        except glance_exceptions.NotFound:
            # ignore exception
            pass
    else:
        filters = {'container_format': 'docker'}
        images = list(glance.images.list(filters=filters))
        if exact_match:
            images = [i for i in images if i.name == image_ident]
        else:
            images = [i for i in images if image_ident in i.name]
        if tag and len(images) > 1:
            images = [i for i in images if tag in i.tags]
    return images


def create_image(context, image_name):
    """Create an image."""
    glance = create_glanceclient(context)
    return glance.images.create(name=image_name)


def update_image(context, img_id, disk_format,
                 container_format, tags):
    """Update an image (container format, disk format & tags)"""
    glance = create_glanceclient(context)
    return glance.images.update(img_id, disk_format=disk_format,
                                container_format=container_format, tags=tags)


def upload_image_data(context, img_id, data):
    """Upload an image."""
    LOG.debug('Upload image %s ', img_id)
    glance = create_glanceclient(context)
    return glance.images.upload(img_id, data)


def download_image_in_chunks(context, img_id):
    """Download image in chunks."""
    LOG.debug('Download image %s', img_id)
    glance = create_glanceclient(context)
    return glance.images.data(img_id)


def delete_image(context, img_id):
    """Delete an image."""
    LOG.debug('Delete image %s', img_id)
    glance = create_glanceclient(context)
    return glance.images.delete(img_id)
