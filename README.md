# spin-db

[![Build docker and push](https://github.com/iliadmitriev/spin-db/actions/workflows/docker-build-push.yml/badge.svg)](https://github.com/iliadmitriev/spin-db/actions/workflows/docker-build-push.yml)

Database package cluster made to provide:
* docker based and run in kubernetes environment
* autoscaling
* high availability 
* high load, connection pooling
* incremental backups
* failover and switchover
* multi architecture x86_64, arm64

Powered by:
* [postgresSQL 13.3](https://www.postgresql.org)
* [patroni 2.1.0](https://patroni.readthedocs.io/en/latest/)
* [etcd 3.5](https://etcd.io)
* [pgBouncer 1.15.0](https://www.pgbouncer.org/2020/11/pgbouncer-1-15-0)
