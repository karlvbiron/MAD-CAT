class AttackFactory:
    """
    Factory class for creating the appropriate attacker instance based on service type.
    """
    
    _registered_attackers = {}
    
    @classmethod
    def register_attacker(cls, attacker_class):
        """
        Register an attacker class with the factory.
        
        Args:
            attacker_class: A BaseAttacker subclass
        """
        service_name = attacker_class.get_service_name()
        cls._registered_attackers[service_name] = attacker_class
    
    @classmethod
    def create_attacker(cls, service_name, host, port=None, username=None, password=None):
        """
        Create and return an appropriate attacker instance.
        
        Args:
            service_name (str): Name of the service to attack
            host (str): Target host IP address
            port (int, optional): Target port number
            username (str, optional): Username for authentication
            password (str, optional): Password for authentication
            
        Returns:
            BaseAttacker: An instance of the appropriate attacker
            
        Raises:
            ValueError: If service_name is not supported
        """
        if service_name not in cls._registered_attackers:
            supported = ", ".join(cls._registered_attackers.keys())
            raise ValueError(f"Unsupported service: {service_name}. Supported services: {supported}")
        
        attacker_class = cls._registered_attackers[service_name]
        
        # If port is None, use the default port for this service
        if port is None:
            port = attacker_class.get_default_port()
            
        return attacker_class(host, port, username, password)
    
    @classmethod
    def list_supported_services(cls):
        """
        List all supported services.
        
        Returns:
            list: List of service names
        """
        return list(cls._registered_attackers.keys())