#!/bin/sh

echo "Starting Redis server..."

# Start Redis server in the background
redis-server --bind 0.0.0.0 &

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
while ! redis-cli ping > /dev/null 2>&1; do
  sleep 1
done

echo "Redis is ready! Loading initial data..."

# Run the initialization script
sh /redis-init.sh

echo "Redis setup complete and running."

# Wait for the Redis server process to keep container alive
wait
