# Import the attackers
from attackers.mongodb import MongoDBAttacker
from attackers.elasticsearch import ElasticsearchAttacker
from attackers.cassandra import CassandraAttacker
from attackers.redis import RedisAttacker
from attackers.couchdb import CouchDBAttacker
from attackers.hadoop import HadoopAttacker
from core.attack_factory import AttackFactory

# Register all attackers with the factory
AttackFactory.register_attacker(MongoDBAttacker)
AttackFactory.register_attacker(ElasticsearchAttacker)
AttackFactory.register_attacker(CassandraAttacker)
AttackFactory.register_attacker(RedisAttacker)
AttackFactory.register_attacker(CouchDBAttacker)
AttackFactory.register_attacker(HadoopAttacker)

__all__ = ['MongoDBAttacker', 'ElasticsearchAttacker', 'CassandraAttacker', 'RedisAttacker', 'CouchDBAttacker', 'HadoopAttacker']