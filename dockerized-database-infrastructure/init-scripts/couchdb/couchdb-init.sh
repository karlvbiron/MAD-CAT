#!/bin/bash

# Wait a bit for CouchDB to be fully ready
sleep 5

# Create database
curl -X PUT http://admin:password@localhost:5984/my_database

# Insert test documents
curl -X POST http://admin:password@localhost:5984/my_database \
  -H "Content-Type: application/json" \
  -d '{"firstName": "John", "lastName": "Doe", "email": "john@doe.com", "phoneNumber": "0123456789"}'

curl -X POST http://admin:password@localhost:5984/my_database \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Jane", "lastName": "Doe", "email": "jane@doe.com", "phoneNumber": "9876543210"}'

curl -X POST http://admin:password@localhost:5984/my_database \
  -H "Content-Type: application/json" \
  -d '{"firstName": "James", "lastName": "Bond", "email": "james.bond@mi6.co.uk", "phoneNumber": "0612345678"}'

echo "CouchDB data initialized successfully!"
