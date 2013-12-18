#!/bin/bash
source /usr/local/bin/config_env

RUN_SELENIUM=${RUN_SELENIUM:-}

cd $APP_DIR/deploy
$VE_DIR/bin/pip install -r requirements-test.txt

cd $APP_DIR
cp dev_settings_test.py test_settings.py
cat << EOF >> test_settings.py
BROKER_HOST = "$TEST_IPADDR"
BROKER_PORT = $TEST_BROKER_PORT
BROKER_USER = 'guest'
BROKER_PASSWORD = 'guest'

HAYSTACK_SOLR_URL = "http://$TEST_IPADDR:$TEST_SOLR_PORT/solr/"

INSTALLED_APPS = INSTALLED_APPS + ('django_nose','webdriver_testing')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '$TEST_IPADDR:$TEST_MEMCACHED_PORT'
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
NOSE_ARGS = ['--logging-filter=test_steps, -remote_connection, '
             '-selenium.webdriver.remote.remote_connection',
             '--with-xunit',
             '--xunit-file=nosetests.xml',
            ]

EOF

CMD="$VE_DIR/bin/python manage.py test search subtitles auth comments messages profiles statistic teams videos widget ted cogi apiv2 --settings=test_settings --with-xunit"

if [ ! -z "$RUN_SELENIUM" ] ; then
    echo "Running Selenium tests..."
    # install xvfb
    DEBIAN_FRONTEND=noninteractive apt-get install -y xvfb python-software-properties dbus-x11 x11-xserver-utils flashplugin-installer
    apt-get install -y firefox
    sleep 5
    CMD="xvfb-run --auto-servernum --server-args='-screen 0 2048x1600x24' $VE_DIR/bin/python manage.py test webdriver_testing --settings=test_settings --with-xunit"
fi

echo "Running Tests..."
cd $APP_DIR
echo $CMD
/bin/bash -c "$CMD"
