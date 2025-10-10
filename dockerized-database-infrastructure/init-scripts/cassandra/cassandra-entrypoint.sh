#!/bin/bash
set -e

# Start Cassandra in background
echo "Starting Cassandra..."
docker-entrypoint.sh cassandra -f &
CASSANDRA_PID=$!

# Function to check if Cassandra is ready
wait_for_cassandra() {
    echo "Waiting for Cassandra to be ready..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if cqlsh -e "DESCRIBE KEYSPACES" > /dev/null 2>&1; then
            echo "Cassandra is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts - waiting 10 seconds..."
        sleep 10
    done

    echo "WARNING: Cassandra did not become ready in time"
    return 1
}

# Wait for Cassandra to be ready
if wait_for_cassandra; then
    echo "Loading initial data..."
    if cqlsh -f /cassandra-init.cql; then
        echo "✓ Initial data loaded successfully!"
    else
        echo "✗ Failed to load initial data"
        echo "  You can manually load it later with:"
        echo "  sudo docker exec -it cassandra cqlsh -f /cassandra-init.cql"
    fi
else
    echo "Cassandra started but CQL shell not ready - data not loaded"
fi

echo "Cassandra is running. Keeping container alive..."

# Keep container running by waiting for Cassandra process
wait $CASSANDRA_PID
