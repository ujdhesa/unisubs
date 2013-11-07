FROM ubuntu:12.04
MAINTAINER Amara "http://amara.org"
RUN (echo "deb http://archive.ubuntu.com/ubuntu precise main universe multiverse" > /etc/apt/sources.list)
RUN (echo "deb-src http://archive.ubuntu.com/ubuntu precise main universe multiverse" >> /etc/apt/sources.list)
RUN apt-get -qq update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
RUN DEBIAN_FRONTEND=noninteractive apt-get -qq -y install wget python-dev python-setuptools make gcc s3cmd libmysqlclient-dev libmemcached-dev supervisor libxml2-dev libxslt-dev zlib1g-dev swig libssl-dev libyaml-dev git-core python-m2crypto subversion openjdk-6-jre libjpeg-dev libfreetype6-dev gettext build-essential gcc
# fix PIL
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libfreetype.so /usr/lib/
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libjpeg.so /usr/lib/
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libz.so /usr/lib/
ENV REVISION staging
ADD . /opt/apps/unisubs
ADD .docker/config_env.sh /usr/local/bin/config_env
ADD .docker/setup.sh /tmp/setup.sh
ADD .docker/build_media.sh /usr/local/bin/build_media
ADD .docker/worker.sh /usr/local/bin/worker
ADD .docker/demo.sh /usr/local/bin/demo
ADD .docker/test_app.sh /usr/local/bin/test_app
ADD .docker/update_translations.sh /usr/local/bin/update_translations
RUN /bin/bash /tmp/setup.sh
ADD .docker/run.sh /usr/local/bin/run

EXPOSE 8000
CMD ["/bin/bash", "/usr/local/bin/run"]
