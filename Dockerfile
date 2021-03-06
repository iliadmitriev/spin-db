FROM alpine:3.14

MAINTAINER Ilia Dmitriev ilia.dmitriev@gmail.com

RUN set -xe \
    
# Install postgres, python3, runit, haproxy, pgbouncer
    && apk add --no-cache musl-locales python3 postgresql \
                    py3-pip runit haproxy pgbouncer \
    && mkdir -p /run/postgresql \
    && chown -R postgres:postgres /run/postgresql \
    && mkdir -p /var/lib/postresql \
    && chown -R postgres:postgres /var/lib/postresql \
    && mkdir -p /var/lib/haproxy \
    && chown -R haproxy:haproxy /var/lib/haproxy \

# Install build dependencies
    && apk add --no-cache --virtual .build-deps \
            build-base python3-dev \
            linux-headers postgresql-dev \
            
# Install patroni, psycopg2, jinja2
    && pip install --no-cache-dir patroni psycopg2 requests patroni[etcd] \
                            jinja2 \
    
# Install etcd
    && echo "Current etcd arch is $(uname -m)" \
    && adduser -D -H -u 120 etcd etcd \
    && case $(uname -m) in \
        "aarch64") \
            wget https://github.com/etcd-io/etcd/releases/download/v3.5.0/etcd-v3.5.0-linux-arm64.tar.gz \
                -O /tmp/etcd-v3.5.0.tar.gz \
            ;; \
        "x86_64") \
            wget https://github.com/etcd-io/etcd/releases/download/v3.5.0/etcd-v3.5.0-linux-amd64.tar.gz \
                -O /tmp/etcd-v3.5.0.tar.gz \
            ;; \
        esac \
    && mkdir /opt/etcd \
    && tar -xvf /tmp/etcd-v3.5.0.tar.gz -C /opt/etcd --strip-components=1 \
    && chown -R etcd:etcd /opt/etcd \
    
# cleanup
    && rm -rf /tmp/* \
    && apk del .build-deps \
    && find /var/log -type f -exec truncate --size 0 {} \; \
    && rm -rf /var/cache/apk/*
    
ENV PATH=$PATH:/opt/etcd \
    LANG=ru_RU.UTF-8 \
    PGDATA=/var/lib/postgresql/data

COPY runit /etc
COPY --chown=postgres postgres0.yml /etc/patroni/postgres0.yml
COPY --chown=postgres pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
COPY --chown=etcd etcd-cluster.py /opt/etcd/etcd-cluster.py
COPY --chown=haproxy haproxy /etc/haproxy


RUN chown -R postgres:postgres /etc/patroni \
    && chmod +x /etc/service/*/* \
    && chmod +x /etc/haproxy/haproxy-reloader.py

STOPSIGNAL SIGINT

EXPOSE 5432 8008 8080 2379 2380

CMD ["/sbin/runsvdir", "-P", "/etc/service"]
