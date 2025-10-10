#!/bin/sh

# Initialize Redis with test data
redis-cli HMSET user:1 firstName "John" lastName "Doe" email "john@doe.com" phoneNumber "0123456789"
redis-cli HMSET user:2 firstName "Jane" lastName "Doe" email "jane@doe.com" phoneNumber "9876543210"
redis-cli HMSET user:3 firstName "James" lastName "Bond" email "james.bond@mi6.co.uk" phoneNumber "0612345678"

echo "Redis data initialized successfully!"
