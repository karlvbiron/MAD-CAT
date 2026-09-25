#!/usr/bin/env python3
"""
Shared configuration for MAD-CAT tooling (fetch_data / restore_data / future
UI + scorer). Single source of truth for connection details and seed location,
so IPs and credentials live in exactly one place.

Values match dockerized-database-infrastructure/docker-compose.yml.
"""

import os

MONGODB_CONFIG = {
    "host": "192.168.1.11",
    "port": 27017,
    "username": "root",
    "password": "example",
    "database": "my_database",
    "collection": "my_table",
}

ELASTICSEARCH_CONFIG = {
    "host": "192.168.1.12",
    "port": 9200,
    "index": "my_index",
}

CASSANDRA_CONFIG = {
    "host": "192.168.1.13",
    "port": 9042,
    "keyspace": "my_keyspace",
    "table": "my_table",
}

REDIS_CONFIG = {
    "host": "192.168.1.14",
    "port": 6379,
    "db": 0,
}

COUCHDB_CONFIG = {
    "host": "192.168.1.15",
    "port": 5984,
    "username": "admin",
    "password": "password",
    "database": "my_database",
}

HADOOP_CONFIG = {
    "host": "192.168.1.16",
    "port": 9870,
    "path": "/user/data",
}

# Where generate_seed_data.py writes its manifest. restore_data.py reads the
# seed/count from here so an in-place restore reproduces the exact seeded state.
SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_output")
MANIFEST_PATH = os.path.join(SEED_DIR, "_manifest.json")

# Fallbacks if the manifest is missing (defaults used by generate_seed_data.py).
DEFAULT_SEED = 1337
DEFAULT_COUNT = 25