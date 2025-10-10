#!/bin/bash

# Set Hadoop home
export HADOOP_HOME=/opt/hadoop

# Additional wait to ensure NameNode is stable
sleep 10

# Create directory in HDFS with error checking
echo "Creating HDFS directory..."
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /user/data
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create HDFS directory"
    exit 1
fi

# Create JSON files with test data
cat > /tmp/user1.json << EOF
{"firstName": "John", "lastName": "Doe", "email": "john@doe.com", "phoneNumber": "0123456789"}
EOF

cat > /tmp/user2.json << EOF
{"firstName": "Jane", "lastName": "Doe", "email": "jane@doe.com", "phoneNumber": "9876543210"}
EOF

cat > /tmp/user3.json << EOF
{"firstName": "James", "lastName": "Bond", "email": "james.bond@mi6.co.uk", "phoneNumber": "0612345678"}
EOF

# Upload files to HDFS with error checking
echo "Uploading files to HDFS..."
$HADOOP_HOME/bin/hdfs dfs -put /tmp/user1.json /user/data/user1.json
$HADOOP_HOME/bin/hdfs dfs -put /tmp/user2.json /user/data/user2.json
$HADOOP_HOME/bin/hdfs dfs -put /tmp/user3.json /user/data/user3.json

# Verify upload
echo "Verifying files in HDFS..."
$HADOOP_HOME/bin/hdfs dfs -ls /user/data/

echo "Hadoop HDFS data initialized successfully!"