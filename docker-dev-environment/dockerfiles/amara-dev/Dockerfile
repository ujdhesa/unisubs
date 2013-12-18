FROM amara
MAINTAINER Ben Dean-Kawamura <ben@pculture.org>

ADD sources.list /etc/apt/sources.list
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE49EC21
RUN apt-get -qq update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
RUN DEBIAN_FRONTEND=noninteractive apt-get -qq -y install wget python-dev python-setuptools make gcc s3cmd libmysqlclient-dev libmemcached-dev supervisor libxml2-dev libxslt-dev zlib1g-dev swig libssl-dev libyaml-dev git-core python-m2crypto subversion openjdk-6-jre libjpeg-dev libfreetype6-dev gettext mysql-client
# install python modules
RUN /opt/ve/unisubs/bin/pip install mock nose django-nose
RUN mkdir -p /opt/extras/pictures
RUN mkdir -p /opt/extras/videos
RUN DEBIAN_FRONTEND=noninteractive apt-get install -qq -y  dialog mysql-client firefox flashplugin-installer python-virtualenv xvfb
# install python packages for the dev environment
RUN /opt/ve/unisubs/bin/pip install mock nose django-nose selenium factory_boy
ENV LC_ALL en_US.UTF-8
