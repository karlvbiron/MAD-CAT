#!/usr/bin/env python3
"""
Script to fetch and display data from MongoDB, Elasticsearch, Cassandra, Redis, CouchDB, and Hadoop HDFS in tabular format.
"""
 
import pymongo
import requests
from tabulate import tabulate
import json
import sys
from cassandra.cluster import Cluster
import redis
 
# ANSI color codes
GREEN_BOLD = "\033[1;32m"
RED_BOLD = "\033[1;31m"
RESET = "\033[0m"
 
def colorize_meow(text):
    """Highlight -MEOW occurrences in bold red"""
    return text.replace("-MEOW", f"{RED_BOLD}-MEOW{RESET}")
 
# Configuration based on docker-compose.yml
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
    print(line.replace(title, f"{GREEN_BOLD}{title}{RESET}"))
    print("=" * 80 + "\n")
 
def fetch_mongodb_data():
    """Fetch data from MongoDB and return as a list of dictionaries"""
    print_header("MONGODB DATA")
    
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(
            host=MONGODB_CONFIG["host"],
            port=MONGODB_CONFIG["port"],
            username=MONGODB_CONFIG["username"],
            password=MONGODB_CONFIG["password"],
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        client.admin.command('ping')
        print(f"Connected to MongoDB at {MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}")
        
        # Get database and collection
        db = client[MONGODB_CONFIG["database"]]
        collection = db[MONGODB_CONFIG["collection"]]
        
        # Fetch all documents
        documents = list(collection.find())
        
        if not documents:
            print("No documents found in MongoDB collection")
            return []
        
        # Print table with tabulate
        headers = documents[0].keys()
        # Filter out ObjectId from headers (typically _id)
        headers = [h for h in headers if h != "_id"]
        
        # Prepare rows (exclude _id field)
        rows = []
        for doc in documents:
            row = [doc.get(h, "") for h in headers]
            rows.append(row)
        
        print(colorize_meow(tabulate(rows, headers=headers, tablefmt="grid")))
        print(f"Total records: {len(documents)}")
        
        return documents
        
    except pymongo.errors.ConnectionFailure as e:
        print(f"Failed to connect to MongoDB: {e}")
        return []
    except Exception as e:
        print(f"Error fetching MongoDB data: {e}")
        return []
 
def fetch_elasticsearch_data():
    """Fetch data from Elasticsearch and return as a list of dictionaries"""
    print_header("ELASTICSEARCH DATA")
    
    try:
        # Construct the URL
        base_url = f"http://{ELASTICSEARCH_CONFIG['host']}:{ELASTICSEARCH_CONFIG['port']}"
        index_url = f"{base_url}/{ELASTICSEARCH_CONFIG['index']}/_search"
        
        # Check if Elasticsearch is running
        health_response = requests.get(f"{base_url}/_cluster/health", timeout=5)
        if health_response.status_code != 200:
            print(f"Elasticsearch is not available: Status {health_response.status_code}")
            return []
        
        print(f"Connected to Elasticsearch at {ELASTICSEARCH_CONFIG['host']}:{ELASTICSEARCH_CONFIG['port']}")
        
        # Query all documents (up to 100)
        query = {
            "query": {"match_all": {}},
            "size": 100
        }
        
        # Send the search request
        response = requests.get(
            index_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(query)
        )
        
        if response.status_code != 200:
            print(f"Failed to fetch data from Elasticsearch: Status {response.status_code}")
            return []
        
        # Parse the response
        search_results = response.json()
        hits = search_results.get("hits", {}).get("hits", [])
        
        if not hits:
            print("No documents found in Elasticsearch index")
            return []
        
        # Extract documents from hits
        documents = []
        for hit in hits:
            doc = hit["_source"]
            doc["_id"] = hit["_id"]  # Add the _id field
            documents.append(doc)
        
        # Print table with tabulate
        if documents:
            # Use the first document to determine headers, excluding _id
            headers = [k for k in documents[0].keys() if k != "_id"]
            
            # Prepare rows
            rows = []
            for doc in documents:
                row = [doc.get(h, "") for h in headers]
                rows.append(row)
            
            print(colorize_meow(tabulate(rows, headers=headers, tablefmt="grid")))
            print(f"Total records: {len(documents)}")
        
        return documents
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Elasticsearch: {e}")
        return []
    except Exception as e:
        print(f"Error fetching Elasticsearch data: {e}")
        return []
 
def fetch_cassandra_data():
    """Fetch data from Cassandra and return as a list of dictionaries"""
    print_header("CASSANDRA DATA")
 
    try:
        # Connect to Cassandra
        cluster = Cluster([CASSANDRA_CONFIG["host"]], port=CASSANDRA_CONFIG["port"])
        session = cluster.connect()
 
        print(f"Connected to Cassandra at {CASSANDRA_CONFIG['host']}:{CASSANDRA_CONFIG['port']}")
 
        # Set keyspace
        session.set_keyspace(CASSANDRA_CONFIG["keyspace"])
 
        # Query all rows from the table
        query = f"SELECT * FROM {CASSANDRA_CONFIG['table']}"
        rows = session.execute(query)
 
        # Convert rows to list of dictionaries
        documents = []
        for row in rows:
            doc = {}
            for col in row._fields:
                doc[col] = getattr(row, col)
            documents.append(doc)
 
        if not documents:
            print("No documents found in Cassandra table")
            cluster.shutdown()
            return []
 
        # Print table with tabulate (exclude id field)
        headers = [h for h in documents[0].keys() if h != "id"]
 
        # Prepare rows
        rows_data = []
        for doc in documents:
            row = [doc.get(h, "") for h in headers]
            rows_data.append(row)
 
        print(colorize_meow(tabulate(rows_data, headers=headers, tablefmt="grid")))
        print(f"Total records: {len(documents)}")
 
        cluster.shutdown()
        return documents
 
    except Exception as e:
        print(f"Error fetching Cassandra data: {e}")
        return []
 
def fetch_redis_data():
    """Fetch data from Redis and return as a list of dictionaries"""
    print_header("REDIS DATA")
 
    try:
        # Connect to Redis
        r = redis.Redis(
            host=REDIS_CONFIG["host"],
            port=REDIS_CONFIG["port"],
            db=REDIS_CONFIG["db"],
            decode_responses=True
        )
 
        # Test connection
        r.ping()
        print(f"Connected to Redis at {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
 
        # Get all keys matching user:* pattern
        keys = r.keys("user:*")
 
        if not keys:
            print("No user keys found in Redis")
            return []
 
        # Fetch all user hashes
        documents = []
        for key in sorted(keys):
            user_data = r.hgetall(key)
            user_data['key'] = key  # Add the key name
            documents.append(user_data)
 
        # Print table with tabulate (exclude key field from display)
        headers = [h for h in documents[0].keys() if h != "key"]
 
        # Prepare rows
        rows_data = []
        for doc in documents:
            row = [doc.get(h, "") for h in headers]
            rows_data.append(row)
 
        print(colorize_meow(tabulate(rows_data, headers=headers, tablefmt="grid")))
        print(f"Total records: {len(documents)}")
 
        return documents
 
    except Exception as e:
        print(f"Error fetching Redis data: {e}")
        return []
 
def fetch_couchdb_data():
    """Fetch data from CouchDB and return as a list of dictionaries"""
    print_header("COUCHDB DATA")
 
    try:
        # Construct URL with authentication
        base_url = f"http://{COUCHDB_CONFIG['username']}:{COUCHDB_CONFIG['password']}@{COUCHDB_CONFIG['host']}:{COUCHDB_CONFIG['port']}"
 
        # Test connection
        response = requests.get(f"{base_url}/")
        if response.status_code != 200:
            print(f"CouchDB is not available: Status {response.status_code}")
            return []
 
        print(f"Connected to CouchDB at {COUCHDB_CONFIG['host']}:{COUCHDB_CONFIG['port']}")
 
        # Get all documents from the database
        db_url = f"{base_url}/{COUCHDB_CONFIG['database']}"
        response = requests.get(f"{db_url}/_all_docs?include_docs=true")
 
        if response.status_code != 200:
            print(f"Failed to fetch data from CouchDB: Status {response.status_code}")
            return []
 
        # Parse the response
        results = response.json()
        rows = results.get('rows', [])
 
        if not rows:
            print("No documents found in CouchDB database")
            return []
 
        # Extract documents
        documents = []
        for row in rows:
            doc = row.get('doc', {})
            # Skip design documents
            if doc.get('_id', '').startswith('_design/'):
                continue
            documents.append(doc)
 
        if not documents:
            print("No user documents found in CouchDB database")
            return []
 
        # Print table with tabulate (exclude _id and _rev fields)
        headers = [h for h in documents[0].keys() if h not in ('_id', '_rev')]
 
        # Prepare rows
        rows_data = []
        for doc in documents:
            row = [doc.get(h, "") for h in headers]
            rows_data.append(row)
 
        print(colorize_meow(tabulate(rows_data, headers=headers, tablefmt="grid")))
        print(f"Total records: {len(documents)}")
 
        return documents
 
    except Exception as e:
        print(f"Error fetching CouchDB data: {e}")
        return []
 
def fetch_hadoop_data():
    """Fetch data from Hadoop HDFS and return as a list of dictionaries"""
    print_header("HADOOP HDFS DATA")
 
    try:
        # Construct WebHDFS URL using IP address
        base_url = f"http://{HADOOP_CONFIG['host']}:{HADOOP_CONFIG['port']}/webhdfs/v1"
 
        # List files in the directory
        list_url = f"{base_url}{HADOOP_CONFIG['path']}?op=LISTSTATUS&user.name=root"
        response = requests.get(list_url)
 
        if response.status_code != 200:
            print(f"Hadoop is not available or path doesn't exist: Status {response.status_code}")
            return []
 
        print(f"Connected to Hadoop HDFS at {HADOOP_CONFIG['host']}:{HADOOP_CONFIG['port']}")
 
        # Get list of files
        result = response.json()
        file_statuses = result.get('FileStatuses', {}).get('FileStatus', [])
 
        # Filter only regular files
        files = [fs['pathSuffix'] for fs in file_statuses if fs['type'] == 'FILE']
 
        if not files:
            print("No files found in Hadoop HDFS path")
            return []
 
        # Fetch content of each file with redirect handling
        documents = []
        session = requests.Session()
        
        for filename in files:
            file_url = f"{base_url}{HADOOP_CONFIG['path']}/{filename}?op=OPEN&user.name=root"
            
            # First request to get the redirect location
            response = session.get(file_url, allow_redirects=False)
            
            if response.status_code == 307:  # Temporary Redirect
                # Get the redirect location and replace hostname with IP
                redirect_url = response.headers.get('Location', '')
                # Replace 'hadoop' hostname with IP address
                redirect_url = redirect_url.replace('hadoop:9864', f"{HADOOP_CONFIG['host']}:9864")
                redirect_url = redirect_url.replace('hadoop:9866', f"{HADOOP_CONFIG['host']}:9866")
                
                # Follow the redirect manually
                file_response = session.get(redirect_url)
                
                if file_response.status_code == 200:
                    try:
                        # Try to parse as JSON
                        doc = file_response.json()
                        documents.append(doc)
                    except json.JSONDecodeError:
                        # If not JSON, skip
                        print(f"Warning: {filename} is not valid JSON")
                        continue
            else:
                print(f"Unexpected response for {filename}: {response.status_code}")
 
        if not documents:
            print("No valid JSON documents found in Hadoop HDFS")
            return []
 
        # Print table with tabulate
        headers = list(documents[0].keys())
 
        # Prepare rows
        rows_data = []
        for doc in documents:
            row = [doc.get(h, "") for h in headers]
            rows_data.append(row)
 
        print(colorize_meow(tabulate(rows_data, headers=headers, tablefmt="grid")))
        print(f"Total records: {len(documents)}")
 
        return documents
 
    except Exception as e:
        print(f"Error fetching Hadoop data: {e}")
        import traceback
        traceback.print_exc()
        return []
 
def verify_data_consistency():
    """Compare data between MongoDB, Elasticsearch, Cassandra, Redis, CouchDB, and Hadoop"""
    print_header("DATA CONSISTENCY CHECK")
 
    mongo_data = fetch_mongodb_data()
    es_data = fetch_elasticsearch_data()
    cassandra_data = fetch_cassandra_data()
    redis_data = fetch_redis_data()
    couchdb_data = fetch_couchdb_data()
    hadoop_data = fetch_hadoop_data()
 
    if not mongo_data or not es_data or not cassandra_data or not redis_data or not couchdb_data or not hadoop_data:
        print("Cannot compare data: One or more data sources are empty")
        return
 
    # Get all emails from each database (excluding None values)
    mongo_emails = {doc.get("email") for doc in mongo_data if "email" in doc and doc.get("email")}
    es_emails = {doc.get("email") for doc in es_data if "email" in doc and doc.get("email")}
    cassandra_emails = {doc.get("email") for doc in cassandra_data if "email" in doc and doc.get("email")}
    redis_emails = {doc.get("email") for doc in redis_data if "email" in doc and doc.get("email")}
    couchdb_emails = {doc.get("email") for doc in couchdb_data if "email" in doc and doc.get("email")}
    hadoop_emails = {doc.get("email") for doc in hadoop_data if "email" in doc and doc.get("email")}
 
    # Display record counts per database
    print(f"\nRecord counts:")
    print(f"  MongoDB:        {len(mongo_emails)} emails")
    print(f"  Elasticsearch:  {len(es_emails)} emails")
    print(f"  Cassandra:      {len(cassandra_emails)} emails")
    print(f"  Redis:          {len(redis_emails)} emails")
    print(f"  CouchDB:        {len(couchdb_emails)} emails")
    print(f"  Hadoop:         {len(hadoop_emails)} emails")
 
    # Find common records across all databases
    common_all = mongo_emails.intersection(es_emails).intersection(cassandra_emails).intersection(redis_emails).intersection(couchdb_emails).intersection(hadoop_emails)
 
    print(f"\nCommon records across all databases: {len(common_all)}")
    if common_all:
        print("Common email addresses:")
        for email in sorted(common_all):
            print(f"  - {email}")
 
    # Find records unique to each database
    mongo_only = mongo_emails - es_emails - cassandra_emails - redis_emails - couchdb_emails - hadoop_emails
    es_only = es_emails - mongo_emails - cassandra_emails - redis_emails - couchdb_emails - hadoop_emails
    cassandra_only = cassandra_emails - mongo_emails - es_emails - redis_emails - couchdb_emails - hadoop_emails
    redis_only = redis_emails - mongo_emails - es_emails - cassandra_emails - couchdb_emails - hadoop_emails
    couchdb_only = couchdb_emails - mongo_emails - es_emails - cassandra_emails - redis_emails - hadoop_emails
    hadoop_only = hadoop_emails - mongo_emails - es_emails - cassandra_emails - redis_emails - couchdb_emails
 
    if mongo_only:
        print("\nRecords only in MongoDB:")
        for email in sorted(mongo_only):
            print(f"  - {email}")
 
    if es_only:
        print("\nRecords only in Elasticsearch:")
        for email in sorted(es_only):
            print(f"  - {email}")
 
    if cassandra_only:
        print("\nRecords only in Cassandra:")
        for email in sorted(cassandra_only):
            print(f"  - {email}")
 
    if redis_only:
        print("\nRecords only in Redis:")
        for email in sorted(redis_only):
            print(f"  - {email}")
 
    if couchdb_only:
        print("\nRecords only in CouchDB:")
        for email in sorted(couchdb_only):
            print(f"  - {email}")
 
    if hadoop_only:
        print("\nRecords only in Hadoop:")
        for email in sorted(hadoop_only):
            print(f"  - {email}")
 
def main():
    """Main entry point"""
    try:
        # Check for command-line arguments
        if len(sys.argv) > 1:
            if sys.argv[1].lower() == "mongo":
                fetch_mongodb_data()
            elif sys.argv[1].lower() == "es" or sys.argv[1].lower() == "elasticsearch":
                fetch_elasticsearch_data()
            elif sys.argv[1].lower() == "cassandra" or sys.argv[1].lower() == "cass":
                fetch_cassandra_data()
            elif sys.argv[1].lower() == "redis":
                fetch_redis_data()
            elif sys.argv[1].lower() == "couchdb" or sys.argv[1].lower() == "couch":
                fetch_couchdb_data()
            elif sys.argv[1].lower() == "hadoop" or sys.argv[1].lower() == "hdfs":
                fetch_hadoop_data()
            elif sys.argv[1].lower() == "all":
                verify_data_consistency()
            else:
                print(f"Unknown argument: {sys.argv[1]}")
                print("Usage: python fetch_data.py [mongo|es|cassandra|redis|couchdb|hadoop|all]")
        else:
            # Default: fetch from all and verify consistency
            verify_data_consistency()
 
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
 
if __name__ == "__main__":
    main()