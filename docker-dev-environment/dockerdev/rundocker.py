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
import subprocess
import uuid

from dockerdev.paths import cid_path, unisubs_root

def run_docker(arguments, *params, **kwargs):
    cmdline = "docker " + arguments % params
    print '* %s' % cmdline
    subprocess.call(cmdline, shell=True, **kwargs)

def get_docker_output(arguments, *params, **kwargs):
    cmdline = "docker " + arguments % params
    print '* %s' % cmdline
    return subprocess.check_output(cmdline, shell=True, **kwargs)

def run_manage(manage_args, docker_args=None, settings='docker_dev_settings'):
    image_name = 'amara-dev-manage-%s' % (uuid.uuid1().hex[:10],)
    volume_arg = '%s:/opt/apps/unisubs' % (unisubs_root(),)
    run_cmd = [
        'docker',
        'run',
        '-h unisubs.example.com',
        '-i', '-t',
        '-cidfile=%s' % cid_path(image_name),
        '-e', 'DJANGO_SETTINGS_MODULE=%s' % settings,
        '-v', volume_arg,
        '-w', '/opt/apps/unisubs/',
    ]
    if docker_args:
        run_cmd.extend(docker_args)
    run_cmd.extend([
        'amara-dev',
        '/opt/ve/unisubs/bin/python',
        '/opt/apps/unisubs/manage.py',
    ] + manage_args)
    # can't use run_docker here because it will not work with the interactive
    # terminal
    subprocess.check_call(" ".join(run_cmd), shell=True)
    cid = open(cid_path(image_name)).read().strip()
    with open("/dev/null", "w") as dev_null:
        run_docker("stop %s" % cid, stdout=dev_null)
        run_docker("wait %s" % cid, stdout=dev_null)
        run_docker("rm %s" % cid, stdout=dev_null)
    os.remove(cid_path(image_name))
