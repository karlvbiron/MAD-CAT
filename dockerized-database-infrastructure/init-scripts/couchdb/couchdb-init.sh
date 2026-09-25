#!/bin/bash
sleep 5
curl -X PUT http://admin:password@localhost:5984/my_database
curl -X POST http://admin:password@localhost:5984/my_database/_bulk_docs \
  -H "Content-Type: application/json" \
  --data-binary @/couchdb-bulk.json
echo "CouchDB data initialized successfully!"
