#!/usr/bin/python

import sys

from dockerdev.rundocker import run_manage
from dockerdev.containers import initialize_mysql_container

run_manage(['drop_all_tables'])
initialize_mysql_container()
