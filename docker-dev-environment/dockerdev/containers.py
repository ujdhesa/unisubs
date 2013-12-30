# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import os
import time

from dockerdev.paths import cid_path
from dockerdev.rundocker import run_docker, get_docker_output, run_manage

SERVICE_IMAGES = [
    'amara-dev-mysql',
    'amara-dev-rabbitmq',
    'amara-dev-solr',
    'amara-dev-memcache',
]

# map image names to port redirections for them
PORT_MAPPINGS = {
    'amara-dev-mysql': ['51000:3306'],
    'amara-dev-rabbitmq': ['51002:5672'],
    'amara-dev-solr': ['51001:8983'],
    'amara-dev-memcache': ['51003:11211'],
}

def get_cid(image_name):
    if not os.path.exists(cid_path(image_name)):
        return None
    return open(cid_path(image_name)).read().strip()

def get_running_images():
    output = get_docker_output("ps -q")
    return [line.strip() for line in output.split("\n")]

def get_all_images():
    output = get_docker_output("ps -a -q")
    return [line.strip() for line in output.split("\n")]

def initialize_mysql_container():
    run_manage(['syncdb', '--all', '--noinput'])
    run_manage(['migrate', '--fake'])
    run_manage(['setup_current_site', 'unisubs.example.com:8000'])

def run_image(image_name):
    cmd_line = [
        'run',
        '-d',
        '-cidfile=%s' % cid_path(image_name),
        '-h=%s' % image_name,
    ]
    for port_map in PORT_MAPPINGS.get(image_name, []):
        cmd_line.append("-p=%s" % port_map)
    cmd_line.append(image_name)
    run_docker(' '.join(cmd_line))
    if image_name == 'amara-dev-mysql':
        # give mysql a bit of time to startup
        time.sleep(1)
        print '* initializing your database'
        initialize_mysql_container()

def start_container(image_name):
    run_docker("start %s" % (get_cid(image_name)))

def stop_container(image_name):
    run_docker("stop %s" % (get_cid(image_name)))

def remove_container(image_name):
    run_docker("rm %s" % (get_cid(image_name)))
    os.remove(cid_path(image_name))

def start_services():
    currently_running = get_running_images()
    all_images = get_all_images()
    for image_name in SERVICE_IMAGES:
        if not os.path.exists(cid_path(image_name)):
            run_image(image_name)
        else:
            cid = get_cid(image_name)
            if cid not in all_images:
                os.remove(cid_path(image_name))
                run_image(image_name)
            elif cid not in currently_running:
                start_container(image_name)

def stop_services():
    currently_running = get_running_images()
    for image_name in SERVICE_IMAGES:
        if get_cid(image_name) in currently_running:
            stop_container(image_name)

def remove_services():
    stop_services()
    for image_name in SERVICE_IMAGES:
        if get_cid(image_name) is not None:
            remove_container(image_name)
