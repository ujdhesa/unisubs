#!/bin/bash
source /usr/local/bin/config_env
# update
cd $APP_DIR
# get private key from s3 to clone private repo
s3cmd -c /etc/s3cfg get --force s3://amara/admin/keys/amara-transifex /root/.ssh/amara_transifex
chmod 600 /root/.ssh/amara_transifex
cat << EOF > /root/.ssh/config
Host github.com
    IdentityFile /root/.ssh/amara_transifex
EOF

cat << EOF > /root/.gitconfig
[user]
    name = transifex
    email = admin@amara.org
EOF

sed -i 's/.*url.*/url = git@github.com:pculture\/unisubs/g' $APP_DIR/.git/config

./deploy/update_translations.sh
