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

from docker_dev_settings import *

NOSE_ARGS = [
    '--logging-filter=-factory',
]


INSTALLED_APPS += (
    'django_nose',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ":memory:",
        'USER': "",
        'PASSWORD': "",
        'HOST': "",
        'PORT': ''
        }
    }

CACHE_PREFIX = "testcache"
CACHE_TIMEOUT = 60
DEFAULT_PROTOCOL = 'http'
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_PLUGINS = ['utils.test_utils.UnisubsTestPlugin']
CELERY_ALWAYS_EAGER = True

STATIC_URL_BASE = STATIC_URL = "/site_media/"
MEDIA_URL = "/user-data/"
INSTALLED_APPS  + ('django.contrib.staticfiles',

                   )
TEMPLATE_CONTEXT_PROCESSORS + ('django.core.context_processors.static',)


STATICFILES_FINDERS = (
   'django.contrib.staticfiles.finders.FileSystemFinder',

   'django.contrib.staticfiles.finders.AppDirectoriesFinder',
   )


MEDIA_ROOT = rel('user-data/')
STATIC_ROOT = rel('static/')
STATICFILES_DIRS = (rel('media/'), rel('user-data/'))


# Use MD5 password hashing, other algorithms are purposefully slow to increase
# security.  Also include the SHA1 hasher since some of the tests use it.
PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
        'django.contrib.auth.hashers.SHA1PasswordHasher',
)

# Let the nose CaptureLogging plugin handle logging.  It doesn't display
# logging at all, except if there's a test failure.
del LOGGING
NOSE_ARGS = ['--logging-filter=test_steps, -remote_connection, '
             '-selenium.webdriver.remote.remote_connection',
             '--with-xunit',
             '--xunit-file=nosetests.xml',
            ]

