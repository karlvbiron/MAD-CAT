#!/bin/bash

echo "Starting Hadoop services..."

export HADOOP_HOME=/opt/hadoop
export HDFS_NAMENODE_USER=root
export HDFS_DATANODE_USER=root
export HDFS_SECONDARYNAMENODE_USER=root

# Configure HDFS to use our mounted volume
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop

# Set data directories
cat > $HADOOP_CONF_DIR/hdfs-site.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file:///tmp/hadoop-data/dfs/name</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file:///tmp/hadoop-data/dfs/data</value>
    </property>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.permissions.enabled</name>
        <value>false</value>
    </property>
</configuration>
EOF

# Set core-site.xml
cat > $HADOOP_CONF_DIR/core-site.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://hadoop:9000</value>
    </property>
</configuration>
EOF

echo "Configuration files created"

# Format namenode if needed
if [ ! -d "/tmp/hadoop-data/dfs/name/current" ]; then
    echo "Formatting namenode..."
    $HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive
fi

# Start NameNode directly in background
echo "Starting NameNode..."
$HADOOP_HOME/bin/hdfs --daemon start namenode

# Give NameNode time to start
sleep 10

# Start DataNode
echo "Starting DataNode..."
$HADOOP_HOME/bin/hdfs --daemon start datanode

# Wait for services to be ready
echo "Waiting for HDFS services to initialize..."
sleep 10

# Check if NameNode is responding
echo "Checking NameNode status..."
max_attempts=30
attempt=0
until $HADOOP_HOME/bin/hdfs dfsadmin -report &>/dev/null || [ $attempt -eq $max_attempts ]; do
    echo "Waiting for NameNode (attempt $((attempt+1))/$max_attempts)..."
    
    # Check if NameNode process is still running
    if ! pgrep -f "org.apache.hadoop.hdfs.server.namenode.NameNode" > /dev/null; then
        echo "ERROR: NameNode process died. Checking logs..."
        cat /opt/hadoop/logs/hadoop-root-namenode-hadoop.log 2>/dev/null || echo "No namenode logs found"
        exit 1
    fi
    
    sleep 5
    attempt=$((attempt+1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: NameNode failed to respond"
    echo "=== NameNode Logs ==="
    cat /opt/hadoop/logs/hadoop-root-namenode-hadoop.log 2>/dev/null || echo "No logs found"
    echo "=== DataNode Logs ==="
    cat /opt/hadoop/logs/hadoop-root-datanode-hadoop.log 2>/dev/null || echo "No logs found"
    exit 1
fi

echo "HDFS is ready! Loading initial data..."
bash /hadoop-init.sh

echo "Hadoop setup complete and running."

# Show running processes
echo "Running Hadoop processes:"
ps aux | grep java | grep -v grep

tail -f /dev/null