# -*- coding: utf-8 -*-
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

# Settings file for docker development.  This file works with the setup built
# in docker-dev-environment/setup.sh
import subprocess

from settings import *

DEBUG = True
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
SITE_ID = 1
SITE_NAME = 'unisubs-dev'
SECRET_KEY = 'a9yr_yzp2vmj-2q1zq)d2+b^w(7fqu2o&jh18u9dozjbd@-$0!'
STATIC_URL_BASE = STATIC_URL = "http://unisubs.example.com:8000/site_media/"
MEDIA_URL = "http://unisubs.example.com:8000/user-data/"
SITE_PACKAGES_DIR = '/opt/ve/unisubs/lib/python2.7/site-packages/'
CACHE_PREFIX = 'unisubsdevsettings'
CACHE_TIMEOUT = 0
COMPRESS_MEDIA = False
EXTRA_STATIC_URLS = [
    (r'^site_media/admin/(?P<path>.*)$',
     SITE_PACKAGES_DIR + 'django/contrib/admin/static/admin/'),
]
TWITTER_CONSUMER_KEY = '6lHYqtxzQBD3lQ55Chi6Zg'
TWITTER_CONSUMER_SECRET = 'ApkJPIIbBKp3Wph0JBoAg2Nsk1Z5EG6PFTevNpd5Y00'

VIMEO_API_KEY = 'e1a46f832f8dfa99652781ee0b39df12'
VIMEO_API_SECRET = 'bdaeb531298eeee1'

FACEBOOK_APP_KEY = FACEBOOK_APP_ID = '255603057797860'
FACEBOOK_SECRET_KEY = '2a18604dac1ad7e9817f80f3aa3a69f2'

def get_host_address():
    """Get the address of the host machine."""
    output = subprocess.check_output("ip route list", shell=True)
    for line in output.split("\n"):
        components = line.split()
        if components[0] == 'default':
            return components[2]

HOST_ADDRESS = get_host_address()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "amara_dev",
        'USER': "amara_dev",
        'PASSWORD': "amara_dev",
        'HOST': HOST_ADDRESS,
        'PORT': '51000'
        }
    }

HAYSTACK_SOLR_URL = 'http://%s:51001/solr/' % HOST_ADDRESS

BROKER_BACKEND = 'amqplib'
BROKER_HOST = HOST_ADDRESS
BROKER_USER = ''
BROKER_PASSWORD = ''
BROKER_PORT = 51002

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '%s:51003' % (HOST_ADDRESS)
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'sentry': {
            'level': 'DEBUG',
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'bleach': {
            'level': 'ERROR',
            'handlers': ['null'],
            'propagate': False,
        },
        'timing': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False
        },
    },
}
