#!/bin/bash
AWS_ID=${AWS_ACCESS_ID:-}
AWS_KEY=${AWS_SECRET_KEY:-}
S3_PASSPHRASE=${S3_PASSPHRASE:-}
REV=${REVISION:-staging}
SETTINGS_REV=${SETTINGS_REVISION:-$REV}
APP_NAME=unisubs
APP_ROOT=/opt/apps
APP_DIR=$APP_ROOT/$APP_NAME
VE_ROOT=/opt/ve
VE_DIR=$VE_ROOT/$APP_NAME
SMTP_HOST=${SMTP_HOST:-smtp.sendgrid.net}
SMTP_PORT=${SMTP_PORT:-587}
SASL_USER=${SASL_USER:-universalsubtitles}
SASL_PASSWD=${SASL_PASSWD:-}
CELERY_OPTS=${CELERY_OPTS:-}
MAILNAME=${MAILNAME:-pculture.org}
NEW_RELIC_APP_NAME=${NEW_RELIC_APP_NAME:-}
NEW_RELIC_LICENSE_KEY=${NEW_RELIC_LICENSE_KEY:-}
SKIP_CODE_PULL=${SKIP_CODE_PULL:-}

if [ ! -z "$AWS_ID" ] && [ ! -z "$AWS_SECRET_KEY" ] ; then
    # create s3cfg
    cat << EOF > /etc/s3cfg
[default]
access_key = $AWS_ID
acl_public = False
bucket_location = US
cloudfront_host = cloudfront.amazonaws.com
cloudfront_resource = /2008-06-30/distribution
default_mime_type = binary/octet-stream
delete_removed = False
dry_run = False
encoding = UTF-8
encrypt = False
force = False
get_continue = False
gpg_command = /usr/bin/gpg
gpg_decrypt = %(gpg_command)s -d --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s
gpg_encrypt = %(gpg_command)s -c --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s
gpg_passphrase = $S3_PASSPHRASE
guess_mime_type = True
host_base = s3.amazonaws.com
host_bucket = %(bucket)s.s3.amazonaws.com
human_readable_sizes = False
list_md5 = False
preserve_attrs = True
progress_meter = True
proxy_host =
proxy_port = 0
recursive = False
recv_chunk = 4096
secret_key = $AWS_KEY
send_chunk = 4096
simpledb_host = sdb.amazonaws.com
skip_existing = False
urlencoding_mode = normal
use_https = False
verbosity = WARNING
EOF

    chown root:root /etc/s3cfg
    chmod 600 /etc/s3cfg

    mkdir -p /root/.ssh
    # get private key from s3 to clone private repo
    s3cmd -c /etc/s3cfg get --force s3://amara/admin/keys/git-pcf /root/.ssh/git_id_rsa
    chmod 600 /root/.ssh/git_id_rsa
    cat << EOF > /root/.ssh/config
Host github.com
    IdentityFile /root/.ssh/git_id_rsa
EOF
    cd $APP_DIR
    git fetch
    git checkout staging
    git pull --ff-only
    git checkout $REV
    if [ ! -e "unisubs-integration" ]; then
        until git clone git@github.com:pculture/unisubs-integration.git ; do
            echo "Error during clone; trying again in 5 seconds..."
            sleep 5
        done
    fi
    s3cmd -c /etc/s3cfg get --force s3://amara/settings/$SETTINGS_REV/server_local_settings.py server_local_settings.py
    # get transifex config
    s3cmd -c /etc/s3cfg get --force s3://amara/settings/transifexrc /.transifexrc
fi

# checkout respective revisions
if [ -z "$SKIP_CODE_PULL" ] ; then
    cd $APP_DIR
    git fetch
    git checkout staging
    git pull --ff-only
    git checkout $REV
    if [ -e $APP_DIR/unisubs-integration ]; then
        cd $APP_DIR/unisubs-integration
        git fetch
        git checkout master
        INTEGRATION_REV=`cat ../optional/unisubs-integration`
        git reset --hard $INTEGRATION_REV
    fi
fi
cd $APP_DIR
python ./deploy/create_commit_file.py

if [ "$UPDATE_VIRTUALENV" ]; then
    cd deploy
    # install dependencies
    $VE_DIR/bin/pip install -r requirements.txt
    # fix m2crypto
    rm -rf $VE_DIR/lib/python2.7/site-packages/M2Crypto
    ln -s /usr/lib/python2.7/dist-packages/M2Crypto $VE_DIR/lib/python2.7/site-packages/M2Crypto
    cd $APP_DIR
fi
