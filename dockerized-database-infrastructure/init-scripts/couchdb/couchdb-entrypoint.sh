#!/bin/bash

echo "Starting CouchDB..."

# Start CouchDB in the background
/docker-entrypoint.sh /opt/couchdb/bin/couchdb &

COUCHDB_PID=$!

echo "Waiting for CouchDB to be ready..."

# Wait for CouchDB to be ready
until curl -s http://localhost:5984/ > /dev/null 2>&1; do
  sleep 2
done

echo "CouchDB is ready! Loading initial data..."

# Run the initialization script
bash /docker-entrypoint-initdb.d/couchdb-init.sh

echo "CouchDB setup complete and running."

# Keep container running by waiting for CouchDB process
wait $COUCHDB_PID
