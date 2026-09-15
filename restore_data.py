#!/usr/bin/env python3
"""
MAD-CAT Data Restoration Script
Restores all database services to their original seed data after a MAD-CAT simulation.
Supports: MongoDB, Elasticsearch, Cassandra, Redis, CouchDB, Hadoop HDFS
"""
 
import pymongo
import requests
import json
import sys
from cassandra.cluster import Cluster
import redis
 
# ANSI color codes
GREEN_BOLD = "\033[1;32m"
RED_BOLD = "\033[1;31m"
YELLOW_BOLD = "\033[1;33m"
CYAN_BOLD = "\033[1;36m"
RESET = "\033[0m"
 
# Original seed data (from init-scripts)
ORIGINAL_DATA = [
    {"firstName": "John",  "lastName": "Doe",  "email": "john@doe.com",         "phoneNumber": "0123456789"},
    {"firstName": "Jane",  "lastName": "Doe",  "email": "jane@doe.com",         "phoneNumber": "9876543210"},
    {"firstName": "James", "lastName": "Bond", "email": "james.bond@mi6.co.uk", "phoneNumber": "0612345678"},
]
 
# Configuration (matching docker-compose.yml)
MONGODB_CONFIG = {
    "host": "192.168.1.11",
    "port": 27017,
    "username": "root",
    "password": "example",
    "database": "my_database",
    "collection": "my_table"
}
 
ELASTICSEARCH_CONFIG = {
    "host": "192.168.1.12",
    "port": 9200,
    "index": "my_index"
}
 
CASSANDRA_CONFIG = {
    "host": "192.168.1.13",
    "port": 9042,
    "keyspace": "my_keyspace",
    "table": "my_table"
}
 
REDIS_CONFIG = {
    "host": "192.168.1.14",
    "port": 6379,
    "db": 0
}
 
COUCHDB_CONFIG = {
    "host": "192.168.1.15",
    "port": 5984,
    "username": "admin",
    "password": "password",
    "database": "my_database"
}
 
HADOOP_CONFIG = {
    "host": "192.168.1.16",
    "port": 9870,
    "path": "/user/data"
}
 
def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    line = f" {title} ".center(80, "=")
    print(line.replace(title, f"{CYAN_BOLD}{title}{RESET}"))
    print("=" * 80 + "\n")
 
def print_success(msg):
    print(f"{GREEN_BOLD}[+] {msg}{RESET}")

def print_final_success(msg):
    print(f"{GREEN_BOLD}[+] {msg}{RESET} ᓚᘏᗢ")
 
def print_error(msg):
    print(f"{RED_BOLD}[-] {msg}{RESET}")
 
def print_info(msg):
    print(f"{YELLOW_BOLD}[*] {msg}{RESET}")
 
def restore_mongodb():
    """Restore MongoDB to original seed data"""
    print_header("RESTORING MONGODB")
 
    try:
        client = pymongo.MongoClient(
            host=MONGODB_CONFIG["host"],
            port=MONGODB_CONFIG["port"],
            username=MONGODB_CONFIG["username"],
            password=MONGODB_CONFIG["password"],
            serverSelectionTimeoutMS=5000
        )
        client.admin.command('ping')
        print_info(f"Connected to MongoDB at {MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}")
 
        db = client[MONGODB_CONFIG["database"]]
        collection = db[MONGODB_CONFIG["collection"]]
 
        # Drop existing collection and re-insert original data
        collection.drop()
        print_info("Dropped corrupted collection: my_table")
 
        collection.insert_many([doc.copy() for doc in ORIGINAL_DATA])
        print_success(f"Restored {len(ORIGINAL_DATA)} documents to {MONGODB_CONFIG['database']}.{MONGODB_CONFIG['collection']}")
 
        client.close()
        return True
 
    except Exception as e:
        print_error(f"Failed to restore MongoDB: {e}")
        return False
 
def restore_elasticsearch():
    """Restore Elasticsearch to original seed data"""
    print_header("RESTORING ELASTICSEARCH")
 
    try:
        base_url = f"http://{ELASTICSEARCH_CONFIG['host']}:{ELASTICSEARCH_CONFIG['port']}"
 
        # Check connection
        health = requests.get(f"{base_url}/_cluster/health", timeout=5)
        if health.status_code != 200:
            print_error(f"Elasticsearch not available: Status {health.status_code}")
            return False
 
        print_info(f"Connected to Elasticsearch at {ELASTICSEARCH_CONFIG['host']}:{ELASTICSEARCH_CONFIG['port']}")
 
        # Delete the index
        requests.delete(f"{base_url}/{ELASTICSEARCH_CONFIG['index']}")
        print_info(f"Deleted corrupted index: {ELASTICSEARCH_CONFIG['index']}")
 
        # Re-create using bulk API (matching es-bulk_data.json format)
        bulk_data = ""
        for i, doc in enumerate(ORIGINAL_DATA, 1):
            bulk_data += json.dumps({"index": {"_index": ELASTICSEARCH_CONFIG["index"], "_id": str(i)}}) + "\n"
            bulk_data += json.dumps(doc) + "\n"
 
        response = requests.post(
            f"{base_url}/_bulk",
            headers={"Content-Type": "application/json"},
            data=bulk_data
        )
 
        if response.status_code == 200:
            print_success(f"Restored {len(ORIGINAL_DATA)} documents to index '{ELASTICSEARCH_CONFIG['index']}'")
            return True
        else:
            print_error(f"Bulk insert failed: {response.status_code}")
            return False
 
    except Exception as e:
        print_error(f"Failed to restore Elasticsearch: {e}")
        return False
 
def restore_cassandra():
    """Restore Cassandra to original seed data"""
    print_header("RESTORING CASSANDRA")
 
    try:
        cluster = Cluster([CASSANDRA_CONFIG["host"]], port=CASSANDRA_CONFIG["port"])
        session = cluster.connect()
        print_info(f"Connected to Cassandra at {CASSANDRA_CONFIG['host']}:{CASSANDRA_CONFIG['port']}")
 
        # Recreate keyspace and table
        session.execute("""
            CREATE KEYSPACE IF NOT EXISTS my_keyspace
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
        """)
        session.set_keyspace(CASSANDRA_CONFIG["keyspace"])
 
        # Truncate table instead of dropping (preserves schema)
        session.execute(f"TRUNCATE {CASSANDRA_CONFIG['table']}")
        print_info(f"Truncated corrupted table: {CASSANDRA_CONFIG['table']}")
 
        # Re-insert original data
        for i, doc in enumerate(ORIGINAL_DATA, 1):
            session.execute(
                f"INSERT INTO {CASSANDRA_CONFIG['table']} (id, firstName, lastName, email, phoneNumber) "
                f"VALUES (%s, %s, %s, %s, %s)",
                (str(i), doc["firstName"], doc["lastName"], doc["email"], doc["phoneNumber"])
            )
 
        print_success(f"Restored {len(ORIGINAL_DATA)} rows to {CASSANDRA_CONFIG['keyspace']}.{CASSANDRA_CONFIG['table']}")
 
        cluster.shutdown()
        return True
 
    except Exception as e:
        print_error(f"Failed to restore Cassandra: {e}")
        return False
 
def restore_redis():
    """Restore Redis to original seed data"""
    print_header("RESTORING REDIS")
 
    try:
        r = redis.Redis(
            host=REDIS_CONFIG["host"],
            port=REDIS_CONFIG["port"],
            db=REDIS_CONFIG["db"],
            decode_responses=True
        )
        r.ping()
        print_info(f"Connected to Redis at {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
 
        # Delete existing user keys
        existing_keys = r.keys("user:*")
        if existing_keys:
            r.delete(*existing_keys)
            print_info(f"Deleted {len(existing_keys)} corrupted user keys")
 
        # Re-insert original data (matching redis-init.sh HMSET format)
        for i, doc in enumerate(ORIGINAL_DATA, 1):
            r.hset(f"user:{i}", mapping={
                "firstName": doc["firstName"],
                "lastName": doc["lastName"],
                "email": doc["email"],
                "phoneNumber": doc["phoneNumber"]
            })
 
        print_success(f"Restored {len(ORIGINAL_DATA)} user hashes to Redis")
        return True
 
    except Exception as e:
        print_error(f"Failed to restore Redis: {e}")
        return False
 
def restore_couchdb():
    """Restore CouchDB to original seed data"""
    print_header("RESTORING COUCHDB")
 
    try:
        base_url = f"http://{COUCHDB_CONFIG['username']}:{COUCHDB_CONFIG['password']}@{COUCHDB_CONFIG['host']}:{COUCHDB_CONFIG['port']}"
 
        # Check connection
        response = requests.get(f"{base_url}/")
        if response.status_code != 200:
            print_error(f"CouchDB not available: Status {response.status_code}")
            return False
 
        print_info(f"Connected to CouchDB at {COUCHDB_CONFIG['host']}:{COUCHDB_CONFIG['port']}")
 
        db_url = f"{base_url}/{COUCHDB_CONFIG['database']}"
 
        # Delete and recreate the database
        requests.delete(db_url)
        print_info(f"Deleted corrupted database: {COUCHDB_CONFIG['database']}")
 
        requests.put(db_url)
        print_info(f"Recreated database: {COUCHDB_CONFIG['database']}")
 
        # Re-insert original data
        for doc in ORIGINAL_DATA:
            requests.post(
                db_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(doc)
            )
 
        print_success(f"Restored {len(ORIGINAL_DATA)} documents to CouchDB '{COUCHDB_CONFIG['database']}'")
        return True
 
    except Exception as e:
        print_error(f"Failed to restore CouchDB: {e}")
        return False
 
def restore_hadoop():
    """Restore Hadoop HDFS to original seed data"""
    print_header("RESTORING HADOOP HDFS")
 
    try:
        base_url = f"http://{HADOOP_CONFIG['host']}:{HADOOP_CONFIG['port']}/webhdfs/v1"
        session = requests.Session()
 
        # Check connection
        response = requests.get(f"{base_url}{HADOOP_CONFIG['path']}?op=LISTSTATUS&user.name=root", timeout=5)
        if response.status_code != 200:
            print_error(f"Hadoop HDFS not available: Status {response.status_code}")
            return False
 
        print_info(f"Connected to Hadoop HDFS at {HADOOP_CONFIG['host']}:{HADOOP_CONFIG['port']}")
 
        # Get existing files
        result = response.json()
        file_statuses = result.get('FileStatuses', {}).get('FileStatus', [])
        files = [fs['pathSuffix'] for fs in file_statuses if fs['type'] == 'FILE']
 
        # Delete existing files
        for filename in files:
            delete_url = f"{base_url}{HADOOP_CONFIG['path']}/{filename}?op=DELETE&user.name=root"
            requests.delete(delete_url)
 
        if files:
            print_info(f"Deleted {len(files)} corrupted files from HDFS")
 
        # Re-upload original data (matching hadoop-init.sh format: user1.json, user2.json, user3.json)
        for i, doc in enumerate(ORIGINAL_DATA, 1):
            filename = f"user{i}.json"
            create_url = f"{base_url}{HADOOP_CONFIG['path']}/{filename}?op=CREATE&overwrite=true&user.name=root"
 
            # WebHDFS CREATE returns a redirect to the DataNode
            response = session.put(create_url, allow_redirects=False)
 
            if response.status_code == 307:
                redirect_url = response.headers.get('Location', '')
                # Replace hostname with IP address
                redirect_url = redirect_url.replace('hadoop:9864', f"{HADOOP_CONFIG['host']}:9864")
                redirect_url = redirect_url.replace('hadoop:9866', f"{HADOOP_CONFIG['host']}:9866")
 
                # Upload the data to the DataNode
                session.put(
                    redirect_url,
                    headers={"Content-Type": "application/octet-stream"},
                    data=json.dumps(doc)
                )
 
        print_success(f"Restored {len(ORIGINAL_DATA)} JSON files to HDFS '{HADOOP_CONFIG['path']}'")
        return True
 
    except Exception as e:
        print_error(f"Failed to restore Hadoop HDFS: {e}")
        return False
 
# Map service names to restore functions
RESTORE_MAP = {
    "mongo":         restore_mongodb,
    "mongodb":       restore_mongodb,
    "es":            restore_elasticsearch,
    "elasticsearch": restore_elasticsearch,
    "cassandra":     restore_cassandra,
    "cass":          restore_cassandra,
    "redis":         restore_redis,
    "couchdb":       restore_couchdb,
    "couch":         restore_couchdb,
    "hadoop":        restore_hadoop,
    "hdfs":          restore_hadoop,
}
 
def restore_all():
    """Restore all databases"""
    print_header("MAD-CAT DATA RESTORATION")
    print_info("Restoring all databases to original seed data...\n")
 
    results = {}
    for name, func in [
        ("MongoDB",       restore_mongodb),
        ("Elasticsearch", restore_elasticsearch),
        ("Cassandra",     restore_cassandra),
        ("Redis",         restore_redis),
        ("CouchDB",       restore_couchdb),
        ("Hadoop HDFS",   restore_hadoop),
    ]:
        results[name] = func()
 
    # Summary
    print_header("RESTORATION SUMMARY")
    for name, success in results.items():
        status = f"{GREEN_BOLD}RESTORED{RESET}" if success else f"{RED_BOLD}FAILED{RESET}"
        print(f"  {name:20s} {status}")
 
    total = len(results)
    passed = sum(results.values())
    print(f"\n  {passed}/{total} databases restored successfully.")
 
    if passed == total:
        print_final_success(" All data has been un-MEOWed!")
    else:
        print_error(f"\n{total - passed} database(s) failed to restore. Check connectivity and retry.")
 
def main():
    """Main entry point"""
    try:
        if len(sys.argv) > 1:
            target = sys.argv[1].lower()
            if target == "all":
                restore_all()
            elif target in RESTORE_MAP:
                RESTORE_MAP[target]()
            else:
                print(f"Unknown argument: {sys.argv[1]}")
                print("Usage: python restore_data.py [mongo|es|cassandra|redis|couchdb|hadoop|all]")
        else:
            restore_all()
 
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
 
if __name__ == "__main__":
    main()
 