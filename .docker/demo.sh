#!/bin/bash
source /usr/local/bin/config_env
MYSQL_ADMIN_USER=${MYSQL_ADMIN_USER:-}
MYSQL_ADMIN_PASS=${MYSQL_ADMIN_PASS:-}
MYSQL_HOST=`cat $APP_DIR/server_local_settings.py | grep DATABASE_HOST |awk -F= '{ print $2; }' | tr -d "'"`
MYSQL_USER=`cat $APP_DIR/server_local_settings.py | grep DATABASE_USER |awk -F= '{ print $2; }' | tr -d "'"`
MYSQL_PASS=`cat $APP_DIR/server_local_settings.py | grep DATABASE_PASS |awk -F= '{ print $2; }' | tr -d "'"`
MYSQL_DB_NAME=${REV//-/_}

PRE=""
CMD="uwsgi --ini $APP_ROOT/$APP_NAME.ini"
BUCKET_NAME=s3.$REV.amara.org

DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-client

# create s3 bucket
s3cmd -c /etc/s3cfg mb --force s3://$BUCKET_NAME

# set new bucket in settings
sed -i "s/^AWS_STORAGE_BUCKET_NAME.*/AWS_STORAGE_BUCKET_NAME = '$BUCKET_NAME'/g" $APP_DIR/server_local_settings.py
sed -i "s/^AWS_USER_DATA_BUCKET_NAME.*/AWS_USER_DATA_BUCKET_NAME = '$BUCKET_NAME'/g" $APP_DIR/server_local_settings.py
sed -i "s/^DEFAULT_BUCKET.*/DEFAULT_BUCKET = '$BUCKET_NAME'/g" $APP_DIR/server_local_settings.py
sed -i "s/^MEDIA_URL.*/MEDIA_URL = 'http://s3.amazonaws.com/$BUCKET_NAME/'/g" $APP_DIR/server_local_settings.py
sed -i "s/^STATIC_URL.*/STATIC_URL = 'http://s3.amazonaws.com/$BUCKET_NAME/'/g" $APP_DIR/server_local_settings.py

# create db
SQL_CMD="mysql -u$MYSQL_ADMIN_USER -p$MYSQL_ADMIN_PASS -h$MYSQL_HOST"
echo "create user $MYSQL_USER$'%' identified by '$MYSQL_PASS';" | $SQL_CMD
echo "create database $MYSQL_DB_NAME character set utf8 collate utf8_unicode_ci;" | $SQL_CMD
# rds doesn't allow 'grant all'
echo "grant select,insert,update,delete,create,index,alter,create temporary tables,lock tables,execute,create view,show view,create routine,alter routine on $MYSQL_DB_NAME.* to $MYSQL_USER@'%';" | $SQL_CMD

sed -i "s/^DATABASE_NAME.*/DATABASE_NAME = '$MYSQL_DB_NAME'/g" $APP_DIR/server_local_settings.py
sed -i "s/^DATABASE_USER.*/DATABASE_USER = '$MYSQL_USER'/g" $APP_DIR/server_local_settings.py
sed -i "s/^DATABASE_PASSWORD.*/DATABASE_PASSWORD = '$MYSQL_PASS'/g" $APP_DIR/server_local_settings.py

cat << EOF > $APP_ROOT/$APP_NAME.ini
[uwsgi]
master = true
workers = 4
http-socket = 0.0.0.0:8000
add-header = Node: $HOSTNAME
die-on-term = true
enable-threads = true
virtualenv = $VE_DIR
buffer-size = 32768
reload-on-as = 512
no-orphans = true
vacuum = true
pythonpath = $APP_ROOT
wsgi-file = $APP_DIR/deploy/unisubs.wsgi
env = DJANGO_SETTINGS_MODULE=unisubs_settings
static-map = /static=$VE_DIR/lib/python2.7/site-packages/django/contrib/admin/static
EOF

if [ ! -z "$NEW_RELIC_LICENSE_KEY" ] ; then
    $VE_DIR/bin/pip install -U newrelic
    PRE="$VE_DIR/bin/newrelic-admin run-program "
fi

$PRE $CMD
