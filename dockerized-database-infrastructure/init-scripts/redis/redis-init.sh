#!/bin/sh
echo "Loading Redis seed data..."
redis-cli < /redis-data.txt
echo "Redis data initialized successfully!"
