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

from oslo_config import cfg

image_driver_opts = [
    cfg.ListOpt(
        'image_driver_list',
        default=['glance.driver.GlanceDriver', 'docker.driver.DockerDriver'],
        help="""Defines the list of image driver to use for downloading image.
Possible values:
* ``docker.driver.DockerDriver``
* ``glance.driver.GlanceDriver``
Services which consume this:
* ``zun-compute``
Interdependencies to other options:
* None
""")
]

glance_driver_opts = [
    cfg.StrOpt(
        'images_directory',
        default=None,
        help='Shared directory where glance images located. If '
             'specified, docker will try to load the image from '
             'the shared directory by image ID.'),
]

glance_opt_group = cfg.OptGroup(name='glance',
                                title='Glance options for image management')

ALL_OPTS = (glance_driver_opts + image_driver_opts)


def register_opts(conf):
    conf.register_group(glance_opt_group)
    conf.register_opts(glance_driver_opts, group=glance_opt_group)
    conf.register_opts(image_driver_opts)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
