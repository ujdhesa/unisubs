#!/bin/bash
AWS_ID=${AWS_ACCESS_ID:-}
AWS_KEY=${AWS_SECRET_KEY:-}
REV=${REVISION:-staging}
SETTINGS_REV=${SETTINGS_REVISION:-$REV}
RUN_SELENIUM=${RUN_SELENIUM:-$2}
DOCKER_HOST="$1"
if [ ! -z "$DOCKER_HOST" ] ; then
    DOCKER="docker -H $DOCKER_HOST"
    IPADDR="$DOCKER_HOST"
else
    DOCKER="docker"
    IPADDR=`ifconfig docker0 | awk '/inet addr/ {split ($2,A,":"); print A[2]}'`
fi
ROOT=`pwd`
for IMG in amara-app amara-solr amara-rabbitmq amara-memcached
do
    echo "Checking image $IMG..."
    if [ "`$DOCKER images | awk '{ print $1; }' | grep $IMG`" = "" ] ; then
        echo "Building $IMG image..."
        # check for top level image
        if [ "$IMG" = "amara-app" ] ; then
            cd $ROOT && $DOCKER build -t $IMG .
        else
            if [ ! -e "$ROOT/.docker/$IMG" ] ; then
                git clone https://github.com/pculture/docker-$IMG $ROOT/.docker/$IMG
            fi
            cd $ROOT/.docker/$IMG && $DOCKER build -t $IMG .
            # cleanup
            rm -rf $ROOT/.docker/$IMG
        fi
    fi
done

SOLR=$($DOCKER run -i -t -d -p 8983 amara-solr)
SOLR_PORT=$($DOCKER port $SOLR 8983 | awk -F: '{ print $2; }')
RABBITMQ=$($DOCKER run -i -t -d -p 5672 amara-rabbitmq)
RABBITMQ_PORT=$($DOCKER port $RABBITMQ 5672 | awk -F: '{ print $2; }')
MEMCACHED=$($DOCKER run -i -t -d -p 11211 amara-memcached)
MEMCACHED_PORT=$($DOCKER port $MEMCACHED 11211 | awk -F: '{ print $2; }')

echo "Containers: Solr:$SOLR:$SOLR_PORT RabbitMQ:$RABBITMQ:$RABBITMQ_PORT Memcached:$MEMCACHED:$MEMCACHED_PORT"

# run tests
$DOCKER run -i -t -h unisubs.example.com -e AWS_ACCESS_ID=$AWS_ID -e AWS_SECRET_KEY=$AWS_KEY -e REVISION=$REV -e TEST_IPADDR=$IPADDR -e TEST_BROKER_PORT=$RABBITMQ_PORT -e TEST_SOLR_PORT=$SOLR_PORT -e TEST_MEMCACHED_PORT=$MEMCACHED_PORT -e DJANGO_LIVE_TEST_SERVER_ADDRESS="localhost:8090-8100,9000-9200" -e RUN_SELENIUM="$RUN_SELENIUM" amara-app /usr/local/bin/test_app
#$DOCKER run -i -t -h unisubs.example.com -e AWS_ACCESS_ID=$AWS_ID -e AWS_SECRET_KEY=$AWS_KEY -e REVISION=$REV -e TEST_IPADDR=$IPADDR -e TEST_BROKER_PORT=$RABBITMQ_PORT -e TEST_SOLR_PORT=$SOLR_PORT -e TEST_MEMCACHED_PORT=$MEMCACHED_PORT -e DJANGO_LIVE_TEST_SERVER_ADDRESS="localhost:8090-8100,9000-9200" -e RUN_SELENIUM="$RUN_SELENIUM" amara-app bash

RETVAL=$?

sleep 5

for CNT in $SOLR $RABBITMQ $MEMCACHED
do
    $DOCKER kill $CNT
    $DOCKER rm $CNT
done

exit $RETVAL
