FROM alpine:3.7
WORKDIR /opt

RUN apk update \
  && apk add --no-cache\
       bash \
       iproute2 \
       openvswitch \
       py-pip \
       python \
       uwsgi-python \
       libffi-dev \
       openssl-dev \
  && apk add --no-cache --virtual build-deps \
      gcc \
      git \
      linux-headers \
      musl-dev \
      python-dev \
  && pip install -U pip setuptools \
  \
  && git clone https://github.com/openstack/zun \
  && cd /opt/zun \
  && pip install -r ./requirements.txt \
  && python setup.py install \
  && cd / \
  && apk del build-deps

VOLUME /var/log/zun
VOLUME /etc/zun
