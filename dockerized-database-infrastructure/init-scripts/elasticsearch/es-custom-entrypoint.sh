#!/bin/bash

# Start Elasticsearch in the background
/usr/local/bin/docker-entrypoint.sh elasticsearch &

ES_PID=$!

echo "Waiting for Elasticsearch to start..."
until curl -s -X GET 'http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=60s' > /dev/null; do
  echo 'Waiting for Elasticsearch...'
  sleep 5
done

echo "Elasticsearch is up. Creating index with date/numeric detection disabled..."
curl -X PUT 'http://localhost:9200/my_index' -H 'Content-Type: application/json' -d '{"mappings":{"date_detection":false,"numeric_detection":false}}'
echo ""

echo "Running bulk data upload..."
curl -X POST 'http://localhost:9200/_bulk?pretty' -H 'Content-Type: application/json' --data-binary @/usr/share/elasticsearch/config/es-bulk_data.json
echo "Bulk data upload complete. Keeping container running..."

# Keep container running by waiting for the Elasticsearch process
wait $ES_PID
