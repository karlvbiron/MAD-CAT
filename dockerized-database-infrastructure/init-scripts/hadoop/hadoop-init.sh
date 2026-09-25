#!/bin/bash
export HADOOP_HOME=/opt/hadoop
echo "Waiting for HDFS to leave safe mode..."
$HADOOP_HOME/bin/hdfs dfsadmin -safemode wait
echo "Creating HDFS directory..."
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /user/data
echo "Uploading files to HDFS..."
for f in /hadoop-data/*.json; do
    $HADOOP_HOME/bin/hdfs dfs -put -f "$f" /user/data/
done
echo "Verifying files in HDFS..."
$HADOOP_HOME/bin/hdfs dfs -ls /user/data/
echo "Hadoop HDFS data initialized successfully!"
