#!/usr/bin/env python3
"""
MAD-CAT Data Restoration
========================
Restores all database services to their seeded healthcare state IN PLACE, on the
already-running containers, after a MAD-CAT simulation. Much faster than
`docker compose down -v && up` (no container rebuild) and produces the same
state, because the data comes from generate_seed_data.build_all() -- the same
source the container seed files are generated from.

Usage:
    python3 restore_data.py [all|mongo|es|cassandra|redis|couchdb|hadoop]
    (no argument = all)
"""

import json
import os
import sys

import pymongo
import requests
import redis
from cassandra.cluster import Cluster

import config
import generate_seed_data

GREEN = "\033[1;32m"; RED = "\033[1;31m"; YELLOW = "\033[1;33m"; CYAN = "\033[1;36m"; RESET = "\033[0m"


def header(t): print("\n" + "=" * 70 + f"\n{CYAN}{t}{RESET}\n" + "=" * 70)
def ok(m): print(f"{GREEN}[+] {m}{RESET}")
def info(m): print(f"{YELLOW}[*] {m}{RESET}")
def err(m): print(f"{RED}[-] {m}{RESET}")


def load_seed_data():
    """Rebuild the exact dataset the containers were seeded with, using the
    seed/count recorded in the manifest."""
    seed, count = config.DEFAULT_SEED, config.DEFAULT_COUNT
    try:
        with open(config.MANIFEST_PATH) as f:
            m = json.load(f)
        seed = m.get("seed", seed)
        count = m.get("patient_count", count)
        info(f"Using manifest: seed={seed}, patients={count}")
    except Exception:
        info(f"No manifest found; using defaults seed={seed}, patients={count}")
    return generate_seed_data.build_all(count, seed)


def restore_mongodb(data):
    header("RESTORING MONGODB")
    c = config.MONGODB_CONFIG
    try:
        client = pymongo.MongoClient(host=c["host"], port=c["port"],
                                     username=c["username"], password=c["password"],
                                     serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        coll = client[c["database"]][c["collection"]]
        coll.drop()
        coll.insert_many([dict(d) for d in data["mongodb"]])
        ok(f"Restored {len(data['mongodb'])} documents to {c['database']}.{c['collection']}")
        client.close()
        return True
    except Exception as e:
        err(f"MongoDB restore failed: {e}"); return False


def restore_elasticsearch(data):
    header("RESTORING ELASTICSEARCH")
    c = config.ELASTICSEARCH_CONFIG
    base = f"http://{c['host']}:{c['port']}"
    try:
        if requests.get(f"{base}/_cluster/health", timeout=5).status_code != 200:
            err("Elasticsearch not available"); return False
        requests.delete(f"{base}/{c['index']}", timeout=10)
        # Recreate with date/numeric detection disabled so corrupted (non-date)
        # values are accepted -- mirrors es-custom-entrypoint.sh.
        requests.put(f"{base}/{c['index']}",
                     headers={"Content-Type": "application/json"},
                     data=json.dumps({"mappings": {"date_detection": False,
                                                    "numeric_detection": False}}), timeout=10)
        bulk = ""
        for i, doc in enumerate(data["elasticsearch"], 1):
            bulk += json.dumps({"index": {"_index": c["index"], "_id": str(i)}}) + "\n"
            bulk += json.dumps(doc) + "\n"
        r = requests.post(f"{base}/_bulk?refresh=true",
                          headers={"Content-Type": "application/json"}, data=bulk, timeout=30)
        if r.status_code == 200 and not r.json().get("errors"):
            ok(f"Restored {len(data['elasticsearch'])} documents to index '{c['index']}'")
            return True
        err(f"Bulk index reported errors: HTTP {r.status_code}"); return False
    except Exception as e:
        err(f"Elasticsearch restore failed: {e}"); return False


def restore_cassandra(data):
    header("RESTORING CASSANDRA")
    c = config.CASSANDRA_CONFIG
    cols = generate_seed_data.CASSANDRA_COLS
    try:
        cluster = Cluster([c["host"]], port=c["port"])
        session = cluster.connect()
        session.execute("CREATE KEYSPACE IF NOT EXISTS %s WITH replication = "
                        "{'class': 'SimpleStrategy', 'replication_factor': 1}" % c["keyspace"])
        session.set_keyspace(c["keyspace"])
        coldefs = ", ".join(f"{col} text" for col in cols)
        session.execute(f"CREATE TABLE IF NOT EXISTS {c['table']} ({coldefs}, PRIMARY KEY (reading_id))")
        session.execute(f"TRUNCATE {c['table']}")
        placeholders = ", ".join(["%s"] * len(cols))
        stmt = f"INSERT INTO {c['table']} ({', '.join(cols)}) VALUES ({placeholders})"
        for row in data["cassandra"]:
            session.execute(stmt, [row[col] for col in cols])
        ok(f"Restored {len(data['cassandra'])} rows to {c['keyspace']}.{c['table']}")
        cluster.shutdown()
        return True
    except Exception as e:
        err(f"Cassandra restore failed: {e}"); return False


def restore_redis(data):
    header("RESTORING REDIS")
    c = config.REDIS_CONFIG
    try:
        r = redis.Redis(host=c["host"], port=c["port"], db=c["db"], decode_responses=True)
        r.ping()
        existing = r.keys("user:*")
        if existing:
            r.delete(*existing)
        for i, fields in enumerate(data["redis"], 1):
            r.hset(f"user:{i}", mapping=fields)
        ok(f"Restored {len(data['redis'])} user hashes to Redis")
        return True
    except Exception as e:
        err(f"Redis restore failed: {e}"); return False


def restore_couchdb(data):
    header("RESTORING COUCHDB")
    c = config.COUCHDB_CONFIG
    base = f"http://{c['username']}:{c['password']}@{c['host']}:{c['port']}"
    db_url = f"{base}/{c['database']}"
    try:
        if requests.get(f"{base}/", timeout=5).status_code != 200:
            err("CouchDB not available"); return False
        requests.delete(db_url, timeout=10)
        requests.put(db_url, timeout=10)
        r = requests.post(f"{db_url}/_bulk_docs",
                          headers={"Content-Type": "application/json"},
                          data=json.dumps({"docs": [dict(d) for d in data["couchdb"]]}), timeout=30)
        if r.status_code in (200, 201):
            ok(f"Restored {len(data['couchdb'])} documents to CouchDB '{c['database']}'")
            return True
        err(f"Bulk docs failed: HTTP {r.status_code}"); return False
    except Exception as e:
        err(f"CouchDB restore failed: {e}"); return False


def restore_hadoop(data):
    header("RESTORING HADOOP HDFS")
    c = config.HADOOP_CONFIG
    base = f"http://{c['host']}:{c['port']}/webhdfs/v1"
    session = requests.Session()
    try:
        r = session.get(f"{base}{c['path']}?op=LISTSTATUS&user.name=root", timeout=5)
        if r.status_code != 200:
            err("Hadoop HDFS not available"); return False
        existing = [fs["pathSuffix"] for fs in
                    r.json().get("FileStatuses", {}).get("FileStatus", []) if fs["type"] == "FILE"]
        for fn in existing:
            session.delete(f"{base}{c['path']}/{fn}?op=DELETE&user.name=root", timeout=10)
        for i, rec in enumerate(data["hadoop"], 1):
            create = f"{base}{c['path']}/user{i}.json?op=CREATE&overwrite=true&user.name=root"
            resp = session.put(create, allow_redirects=False, timeout=10)
            if resp.status_code == 307:
                redirect = resp.headers.get("Location", "")
                redirect = redirect.replace("hadoop:9864", f"{c['host']}:9864")
                redirect = redirect.replace("hadoop:9866", f"{c['host']}:9866")
                session.put(redirect, headers={"Content-Type": "application/octet-stream"},
                            data=json.dumps(rec), timeout=15)
        ok(f"Restored {len(data['hadoop'])} JSON files to HDFS '{c['path']}'")
        return True
    except Exception as e:
        err(f"Hadoop restore failed: {e}"); return False


def reset_dashboard():
    """Best-effort: tell the dashboard the incident is over so the integrity
    wall clears (otherwise a page refresh replays the last attack's buffered
    events and the panels flip red again). No-op if the dashboard isn't
    running; never affects the restore itself."""
    import urllib.request
    url = os.environ.get("MADCAT_DASHBOARD_URL",
                         "http://127.0.0.1:8000/ingest").replace("/ingest", "/reset")
    try:
        urllib.request.urlopen(
            urllib.request.Request(url, data=b"", method="POST"), timeout=0.5).close()
        ok("Dashboard integrity wall reset")
    except Exception:
        pass  # dashboard down / not in use


RESTORE_MAP = {
    "mongo": restore_mongodb, "mongodb": restore_mongodb,
    "es": restore_elasticsearch, "elasticsearch": restore_elasticsearch,
    "cassandra": restore_cassandra, "cass": restore_cassandra,
    "redis": restore_redis,
    "couchdb": restore_couchdb, "couch": restore_couchdb,
    "hadoop": restore_hadoop, "hdfs": restore_hadoop,
}

ALL = [("MongoDB", restore_mongodb), ("Elasticsearch", restore_elasticsearch),
       ("Cassandra", restore_cassandra), ("Redis", restore_redis),
       ("CouchDB", restore_couchdb), ("Hadoop HDFS", restore_hadoop)]


def main():
    data = load_seed_data()
    target = (sys.argv[1].lower() if len(sys.argv) > 1 else "all")

    if target == "all":
        header("MAD-CAT DATA RESTORATION")
        results = {name: fn(data) for name, fn in ALL}
        header("RESTORATION SUMMARY")
        for name, success in results.items():
            print(f"  {name:16s} {(GREEN + 'RESTORED' if success else RED + 'FAILED') + RESET}")
        passed = sum(results.values()); total = len(results)
        print(f"\n  {passed}/{total} databases restored.")
        if passed == total:
            print(f"{GREEN}[+] All data has been un-MEOWed! \u1652\u140f\u1622{RESET}")
        reset_dashboard()
    elif target in RESTORE_MAP:
        RESTORE_MAP[target](data)
        reset_dashboard()
    else:
        print(f"Unknown target: {target}")
        print("Usage: python3 restore_data.py [all|mongo|es|cassandra|redis|couchdb|hadoop]")


if __name__ == "__main__":
    main()