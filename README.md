# MAD-CAT </br> [Meow Attack Data Corruption Automation Tool]

![MAD-CAT Banner](https://img.shields.io/badge/Security-MAD--CAT%20Simulation-red)
![Python](https://img.shields.io/badge/Python-3.6%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

MAD-CAT (Meow Attack Data Corruption Automation Tool) is a comprehensive security tool designed to simulate data corruption attacks against multiple database systems. The tool supports both single-target attacks and bulk CSV-based attack campaigns, with support for both credentialed and non-credentialed attack scenarios.

## Supported Database Services

The tool currently supports the following database services:

<div align="center">
  <img src="https://www.vectorlogo.zone/logos/mongodb/mongodb-ar21.svg" alt="MongoDB" width="180"/>
  <img src="https://www.vectorlogo.zone/logos/elastic/elastic-ar21.svg" alt="Elasticsearch" width="180"/>
  <img src="https://www.vectorlogo.zone/logos/apache_cassandra/apache_cassandra-ar21.svg" alt="Cassandra" width="180"/>
  </br>
  <img src="https://www.vectorlogo.zone/logos/redis/redis-ar21.svg" alt="Redis" width="180"/>
  <img src="https://www.vectorlogo.zone/logos/apache_couchdb/apache_couchdb-ar21.svg" alt="CouchDB" width="180"/>
  <img src="https://www.vectorlogo.zone/logos/apache_hadoop/apache_hadoop-ar21.svg" alt="Hadoop" width="180"/>
</div>

- **MongoDB** (port 27017)
- **Elasticsearch** (port 9200)
- **Cassandra** (port 9042)
- **Redis** (port 6379)
- **CouchDB** (port 5984)
- **Hadoop HDFS** (port 9870)

## Installation

```bash
# Clone the repository
git clone https://github.com/karlvbiron/MAD-CAT.git

# Navigate to the tool directory
cd MAD-CAT

# Install dependencies
pip install -r requirements.txt
```

## Command Line Arguments

| Argument | Description |
|----------|-------------|
| `-l`, `--list` | List supported database services |
| `-c`, `--csv` | CSV file containing target list (format: ip,service,port,username,password) |
| `-t`, `--target` | Target host IP address (for single target mode) |
| `-s`, `--service` | Database service to attack (e.g., mongodb, elasticsearch, cassandra, redis, couchdb, hadoop) |
| `-p`, `--port` | Port number (if not default) |
| `-u`, `--username` | Username for authentication |
| `-pw`, `--password` | Password for authentication |
| `-v`, `--verbose` | Enable verbose output |

## Usage Examples

### List Supported Services

```bash
python mad_cat.py -l
```

### Single Target Attacks

#### MongoDB Simulation (Credentialed)

```bash
python mad_cat.py -t 192.168.1.11 -s mongodb -u root -pw example
```

#### Elasticsearch Simulation (Non-Credentialed)

```bash
python mad_cat.py -t 192.168.1.12 -s elasticsearch
```

#### Cassandra Simulation

```bash
python mad_cat.py -t 192.168.1.13 -s cassandra
```

#### Redis Simulation

```bash
python mad_cat.py -t 192.168.1.14 -s redis
```

#### CouchDB Simulation (Credentialed)

```bash
python mad_cat.py -t 192.168.1.15 -s couchdb -u admin -pw password
```

#### Hadoop HDFS Simulation

```bash
python mad_cat.py -t 192.168.1.16 -s hadoop
```

### CSV Bulk Attack Mode

Attack multiple targets using a CSV file:

```bash
python mad_cat.py -c list.csv
```

#### CSV File Format

The CSV file should contain one target per line with the following format:

```csv
192.168.1.11,mongodb,27017,"root","example"
192.168.1.12,elasticsearch,9200,"",""
192.168.1.13,cassandra,9042,"",""
192.168.1.14,redis,6379,"",""
192.168.1.15,couchdb,5984,"admin","password"
192.168.1.16,hadoop,9870,"",""
```

**Format**: `ip,service,port,username,password`

- Leave username/password as empty strings (`""`) for non-credentialed attacks

## Project Structure

```
MAD-CAT/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── base_attacker.py          # Abstract base class for all attackers
│   └── attack_factory.py         # Factory pattern for attacker creation
├── attackers/
│   ├── __init__.py               # Attacker registration
│   ├── mongodb.py                # MongoDB attacker implementation
│   ├── elasticsearch.py          # Elasticsearch attacker implementation
│   ├── cassandra.py              # Cassandra attacker implementation
│   ├── redis.py                  # Redis attacker implementation
│   ├── couchdb.py                # CouchDB attacker implementation
│   └── hadoop.py                 # Hadoop HDFS attacker implementation
├── utils/
│   ├── __init__.py
│   └── logging.py                # Logging configuration
├── dockerized-database-infrastructure/
│   ├── docker-compose.yml        # Docker Compose configuration
│   └── init-scripts/
│       ├── mongodb/
│       │   └── mongodb-init.js
│       ├── elasticsearch/
│       │   ├── es-custom-entrypoint.sh
│       │   └── es-bulk_data.json
│       ├── cassandra/
│       │   ├── cassandra-entrypoint.sh
│       │   └── cassandra-init.cql
│       ├── couchdb/
│       │   ├── couchdb-entrypoint.sh
│       │   └── couchdb-init.sh
│       ├── hadoop/
│       │   ├── hadoop-entrypoint.sh
│       │   └── hadoop-init.sh
│       └── redis/
│           ├── redis-entrypoint.sh
│           └── redis-init.sh
├── mad_cat.py                    # Main entry point
├── fetch_data.py                 # Utility to fetch and verify database data
├── list.csv                      # Example CSV file for bulk attacks
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Features

- ✅ **6 Database Services**: MongoDB, Elasticsearch, Cassandra, Redis, CouchDB, Hadoop HDFS
- ✅ **Credentialed & Non-Credentialed Attacks**: Supports both authentication modes
- ✅ **Single Target Mode**: Attack individual database instances
- ✅ **CSV Bulk Attack Mode**: Attack multiple targets from a CSV file
- ✅ **Factory Pattern Architecture**: Easy to extend with new database attackers
- ✅ **Comprehensive Logging**: Timestamped logs saved to `logs/` directory
- ✅ **User Confirmation**: Requires explicit confirmation before executing attacks
- ✅ **Attack Statistics**: Detailed reporting of databases, collections, and records affected
- ✅ **Default Port Support**: Automatically uses standard ports if not specified

## How It Works

MAD-CAT simulates a data corruption attack by:

1. **Connecting** to the target database using provided credentials (or attempting anonymous access)
2. **Enumerating** all databases and collections/tables (excluding system databases)
3. **Corrupting** data by replacing string/numeric values with random alphanumeric strings followed by "-MEOW"
4. **Reporting** statistics on databases processed, collections affected, and records modified

### Attack Workflow

```
Target → Connect → List Databases → For Each Database:
                                      ├─ List Collections
                                      └─ For Each Collection:
                                          ├─ Fetch All Records
                                          ├─ Replace Values with {random}-MEOW
                                          └─ Update Records
```

## Default Ports

| Service | Default Port |
|---------|--------------|
| MongoDB | 27017 |
| Elasticsearch | 9200 |
| Cassandra | 9042 |
| Redis | 6379 |
| CouchDB | 5984 |
| Hadoop HDFS | 9870 |

## Additional Tools

### fetch_data.py

A utility script to fetch and display data from all supported databases:

```bash
# Fetch from all databases and verify consistency
python fetch_data.py all

# Fetch from specific database
python fetch_data.py mongo
python fetch_data.py elasticsearch
python fetch_data.py cassandra
python fetch_data.py redis
python fetch_data.py couchdb
python fetch_data.py hadoop
```

## Disclaimer

This tool is provided for **EDUCATIONAL PURPOSES ONLY**. It is designed to demonstrate a type of cyber attack in a controlled environment to help improve security awareness and defensive measures. Using this tool against systems without proper authorization is illegal and unethical. The authors and contributors are not responsible for any misuse of this software.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Created by Karl Biron
