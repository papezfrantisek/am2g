# syntax=docker/dockerfile:1
FROM alpine
LABEL Maintainer="frantisek@elkjop.no"
LABEL version="1.0"

ENV prometheus_version 2.8.1
ENV PYTHONUNBUFFERED=1
ENV AM2G_DEBUG=N
ENV HOME='/am2g'

RUN adduser -s /bin/false -D -H prometheus \
    && adduser -s /bin/false -D -H node_exporter \
    && apk update \
    && apk --no-cache add curl \
    && curl -LO https://github.com/prometheus/prometheus/releases/download/v${prometheus_version}/prometheus-${prometheus_version}.linux-amd64.tar.gz \
    && tar -xvzf prometheus-${prometheus_version}.linux-amd64.tar.gz \
    && mkdir -p /etc/prometheus /var/lib/prometheus \
    && cp prometheus-${prometheus_version}.linux-amd64/promtool /usr/local/bin/ \
    && cp prometheus-${prometheus_version}.linux-amd64/prometheus /usr/local/bin/ \
    && cp -R prometheus-${prometheus_version}.linux-amd64/console_libraries/ /etc/prometheus/ \
    && cp -R prometheus-${prometheus_version}.linux-amd64/consoles/ /etc/prometheus/ \
    && rm -rf prometheus-${prometheus_version}.linux-amd64* \
    && chown prometheus:prometheus /usr/local/bin/prometheus \
    && chown prometheus:prometheus /usr/local/bin/promtool \
    && chown -R prometheus:prometheus /etc/prometheus \
    && chown prometheus:prometheus /var/lib/prometheus \
    && apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python \
    && python3 -m ensurepip \
    && pip3 install --no-cache --upgrade pip setuptools \
    && pip3 install requests prometheus_client futures3 \
    && apk del curl \
    && mkdir /am2g/data \
    && export AM2G_DEBUG=N

VOLUME /etc/prometheus
VOLUME /var/lib/prometheus
VOLUME /am2g


ADD conf/prometheus.yml /etc/prometheus/ 
ADD am2g /am2g/

ENTRYPOINT /usr/local/bin/prometheus \ 
            --config.file /etc/prometheus/prometheus.yml \ 
            --storage.tsdb.path /var/lib/prometheus/ \
            --web.console.libraries=/usr/share/prometheus/console_libraries \
            --web.console.templates=/usr/share/prometheus/consoles & python /am2g/am2g


EXPOSE 9090
EXPOSE 8000
