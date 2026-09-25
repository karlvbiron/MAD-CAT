#!/usr/bin/env python3
"""
MAD-CAT Healthcare Seed Data Generator
======================================
Generates HIPAA-shaped synthetic patient data for all six MAD-CAT database
services, each written in the file format that service's loader expects.

Design constraints (derived from the MAD-CAT attacker audit):
  * All corrupt-target values are FLAT str/int/float. The MEOW attackers only
    rewrite flat str/int/float values; nested objects/arrays survive.
  * Cassandra columns are all declared TEXT (the Cassandra attacker SKIPS
    numeric-typed columns); the primary key is a synthetic id so real PHI lives
    in corruptible, non-key columns.
  * DB/collection/index/key names match docker-compose + fetch_data config
    (my_database / my_table / my_index / my_keyspace / user:* / /user/data).

The record-BUILDING logic (build_all) is separated from the file-WRITING logic
so restore_data.py can reuse build_all() as the single source of truth: restoring
in place reproduces exactly what `docker compose down -v && up` would seed.

Dependencies: faker only.  Deterministic via --seed.
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta, date

from faker import Faker

HIPAA_IDENTIFIER_MAP = {
    "firstName": "1 - Names",
    "lastName": "1 - Names",
    "address": "2 - Geographic subdivisions smaller than a state",
    "city": "2 - Geographic subdivisions smaller than a state",
    "zip": "2 - Geographic subdivisions smaller than a state",
    "dob": "3 - Dates related to an individual (birth date)",
    "admission_date": "3 - Dates related to an individual",
    "discharge_date": "3 - Dates related to an individual",
    "phoneNumber": "4 - Telephone numbers",
    "email": "6 - Electronic mail addresses",
    "ssn": "7 - Social Security numbers",
    "mrn": "8 - Medical record numbers",
    "health_plan_id": "9 - Health plan beneficiary numbers",
    "account_number": "10 - Account numbers",
    "device_id": "14 - Device identifiers and serial numbers",
    "ip_address": "15 - IP addresses",
    "npi": "18 - Any other unique identifying number (provider NPI)",
    "patient_id": "18 - Any other unique identifying number (internal MRN link)",
}

ICD10 = [
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential (primary) hypertension"),
    ("J45.909", "Unspecified asthma, uncomplicated"),
    ("N18.3", "Chronic kidney disease, stage 3"),
    ("F41.1", "Generalized anxiety disorder"),
    ("M54.5", "Low back pain"),
    ("K21.9", "Gastro-esophageal reflux disease without esophagitis"),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery"),
    ("E78.5", "Hyperlipidemia, unspecified"),
    ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
]
MEDICATIONS = [
    "Metformin 500mg", "Lisinopril 10mg", "Atorvastatin 20mg", "Albuterol HFA",
    "Omeprazole 20mg", "Amlodipine 5mg", "Sertraline 50mg", "Levothyroxine 75mcg",
    "Gabapentin 300mg", "Furosemide 40mg",
]
CPT = ["99213", "99214", "93000", "80053", "85025", "71046", "36415", "99396"]
DEPARTMENTS = [
    "Cardiology", "Endocrinology", "Nephrology", "Pulmonology",
    "Internal Medicine", "Emergency", "Radiology", "Behavioral Health",
]
DOC_TYPES = ["Discharge Summary", "Progress Note", "Lab Report",
             "Radiology Report", "Consultation Note"]
CLAIM_STATUS = ["Submitted", "Adjudicated", "Paid", "Denied", "Pending"]

CLASSIFICATION = "PHI"

# Cassandra column order (all TEXT). Exposed so restore_data.py builds the same
# schema and INSERT column list.
CASSANDRA_COLS = ["reading_id", "patient_id", "mrn", "firstName", "lastName",
                  "email", "phoneNumber", "heart_rate", "blood_pressure", "spo2",
                  "temperature", "respiratory_rate", "device_id", "recorded_at",
                  "data_classification"]


def build_roster(fake, n):
    patients = []
    for i in range(1, n + 1):
        first = fake.first_name()
        last = fake.last_name()
        email = f"{first}.{last}.{i}@example-health.org".lower()
        # Fixed absolute anchors (not "-90d"/age-relative) so output is
        # reproducible across days -- restore must match the seeded files exactly.
        dob = fake.date_between(start_date=date(1930, 1, 1), end_date=date(2019, 12, 31))
        admit = fake.date_time_between(start_date=datetime(2026, 6, 1),
                                       end_date=datetime(2026, 9, 13))
        discharge = admit + timedelta(days=random.randint(1, 9))
        icd = random.choice(ICD10)
        patients.append({
            "patient_id": f"PT-{i:05d}",
            "mrn": f"MRN{random.randint(1000000, 9999999)}",
            "firstName": first,
            "lastName": last,
            "email": email,
            "phoneNumber": fake.numerify("(###) ###-####"),
            "ssn": fake.ssn(),
            "dob": dob.isoformat(),
            "address": fake.street_address(),
            "city": fake.city(),
            "zip": fake.postcode(),
            "health_plan_id": f"HP-{fake.numerify('##########')}",
            "account_number": f"ACCT-{fake.numerify('########')}",
            "diagnosis_code": icd[0],
            "diagnosis": icd[1],
            "medication": random.choice(MEDICATIONS),
            "attending_physician": f"Dr. {fake.last_name()}",
            "npi": fake.numerify("##########"),
            "admission_date": admit.date().isoformat(),
            "discharge_date": discharge.date().isoformat(),
            "data_classification": CLASSIFICATION,
        })
    return patients


def core_identity(p):
    return {
        "patient_id": p["patient_id"],
        "mrn": p["mrn"],
        "firstName": p["firstName"],
        "lastName": p["lastName"],
        "email": p["email"],
        "phoneNumber": p["phoneNumber"],
    }


# --------------------------------------------------------------------------- #
# Record builders (reused by restore). Order of calls in build_all preserves the
# RNG sequence, so output is identical to prior versions for a given seed/count.
# --------------------------------------------------------------------------- #
def build_mongodb(patients):
    return [dict(p) for p in patients]


def build_elasticsearch(patients):
    records = []
    for p in patients:
        doc = core_identity(p)
        doc.update({
            "document_type": random.choice(DOC_TYPES),
            "author": p["attending_physician"],
            "note_text": (f"{p['firstName']} {p['lastName']} (MRN {p['mrn']}) "
                          f"seen for {p['diagnosis']} ({p['diagnosis_code']}). "
                          f"Plan: continue {p['medication']}."),
            "created_at": p["admission_date"],
            "data_classification": CLASSIFICATION,
        })
        records.append(doc)
    return records


def build_cassandra(patients, fake):
    records = []
    for i, p in enumerate(patients, 1):
        ident = core_identity(p)
        row = {
            "reading_id": f"VIT-{i:05d}",
            **ident,
            "heart_rate": str(random.randint(55, 110)),
            "blood_pressure": f"{random.randint(105, 150)}/{random.randint(65, 95)}",
            "spo2": str(random.randint(92, 100)),
            "temperature": f"{round(random.uniform(97.0, 100.4), 1)}",
            "respiratory_rate": str(random.randint(12, 22)),
            "device_id": f"MON-{random.randint(1000, 9999)}",
            "recorded_at": fake.date_time_between(
                start_date=datetime(2026, 1, 1),
                end_date=datetime(2026, 9, 1)).isoformat(timespec="seconds"),
            "data_classification": CLASSIFICATION,
        }
        records.append(row)
    return records


def build_redis(patients, fake):
    records = []
    for p in patients:
        ident = core_identity(p)
        fields = {
            **ident,
            "session_id": f"SESS-{random.randint(100000, 999999)}",
            "clinician": p["attending_physician"],
            "login_time": fake.date_time_between(
                start_date=datetime(2026, 1, 1),
                end_date=datetime(2026, 9, 1)).isoformat(timespec="seconds"),
            "ip_address": f"10.0.{random.randint(1,254)}.{random.randint(1,254)}",
            "department": random.choice(DEPARTMENTS),
            "data_classification": CLASSIFICATION,
        }
        records.append(fields)
    return records


def build_couchdb(patients):
    docs = []
    for p in patients:
        d = core_identity(p)
        d.update({
            "appointment_id": f"APPT-{random.randint(100000, 999999)}",
            "appointment_date": p["discharge_date"],
            "department": random.choice(DEPARTMENTS),
            "provider": p["attending_physician"],
            "reason": p["diagnosis"],
            "refill_request": p["medication"],
            "data_classification": CLASSIFICATION,
        })
        docs.append(d)
    return docs


def build_hadoop(patients):
    recs = []
    for p in patients:
        rec = core_identity(p)
        rec.update({
            "invoice_id": f"INV-{random.randint(100000, 999999)}",
            "account_number": p["account_number"],
            "health_plan_id": p["health_plan_id"],
            "cpt_code": random.choice(CPT),
            "service_date": p["admission_date"],
            "billed_amount": f"{random.randint(120, 9800)}.{random.randint(0,99):02d}",
            "claim_status": random.choice(CLAIM_STATUS),
            "data_classification": CLASSIFICATION,
        })
        recs.append(rec)
    return recs


def build_all(count, seed):
    """Single source of truth. Returns {service: [records]} for the given
    seed/count. Call order preserves the RNG sequence used by the writers."""
    fake = Faker()
    Faker.seed(seed)
    random.seed(seed)
    patients = build_roster(fake, count)
    return {
        "mongodb": build_mongodb(patients),        # no RNG
        "elasticsearch": build_elasticsearch(patients),
        "cassandra": build_cassandra(patients, fake),
        "redis": build_redis(patients, fake),
        "couchdb": build_couchdb(patients),
        "hadoop": build_hadoop(patients),
    }


# --------------------------------------------------------------------------- #
# File writers (thin serializers over the built records).
# --------------------------------------------------------------------------- #
def write_mongodb_file(records, outdir):
    docs = json.dumps(records, indent=2)
    js = (
        "// Auto-generated by generate_seed_data.py -- healthcare PHI seed\n"
        "db = db.getSiblingDB('my_database');\n"
        "db.my_table.drop();\n"
        f"db.my_table.insertMany({docs});\n"
        "print('Seeded ' + db.my_table.countDocuments({}) + ' patient records');\n"
    )
    path = os.path.join(outdir, "mongodb-init.js")
    with open(path, "w") as f:
        f.write(js)
    return path, len(records)


def write_elasticsearch_file(records, outdir):
    lines = []
    for i, doc in enumerate(records, 1):
        lines.append(json.dumps({"index": {"_index": "my_index", "_id": str(i)}}))
        lines.append(json.dumps(doc))
    path = os.path.join(outdir, "es-bulk_data.json")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path, len(records)


def write_cassandra_file(records, outdir):
    def esc(v):
        return str(v).replace("'", "''")
    stmts = [
        "CREATE KEYSPACE IF NOT EXISTS my_keyspace",
        "  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};",
        "USE my_keyspace;",
        "CREATE TABLE IF NOT EXISTS my_table (",
        "    " + ",\n    ".join(f"{c} text" for c in CASSANDRA_COLS) + ",",
        "    PRIMARY KEY (reading_id)",
        ");",
        "",
    ]
    for row in records:
        vals = ", ".join(f"'{esc(row[c])}'" for c in CASSANDRA_COLS)
        stmts.append(f"INSERT INTO my_table ({', '.join(CASSANDRA_COLS)}) VALUES ({vals});")
    path = os.path.join(outdir, "cassandra-init.cql")
    with open(path, "w") as f:
        f.write("\n".join(stmts) + "\n")
    return path, len(records)


def write_redis_file(records, outdir):
    lines = []
    for i, fields in enumerate(records, 1):
        parts = " ".join(f'{k} "{v}"' for k, v in fields.items())
        lines.append(f"HSET user:{i} {parts}")
    path = os.path.join(outdir, "redis-data.txt")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path, len(records)


def write_couchdb_file(records, outdir):
    path = os.path.join(outdir, "couchdb-bulk.json")
    with open(path, "w") as f:
        json.dump({"docs": records}, f, indent=2)
    return path, len(records)


def write_hadoop_file(records, outdir):
    hdir = os.path.join(outdir, "hadoop")
    os.makedirs(hdir, exist_ok=True)
    for i, rec in enumerate(records, 1):
        with open(os.path.join(hdir, f"user{i}.json"), "w") as f:
            json.dump(rec, f)
    return hdir, len(records)


def main():
    ap = argparse.ArgumentParser(description="MAD-CAT healthcare seed generator")
    ap.add_argument("-n", "--count", type=int, default=25,
                    help="number of patients in the roster (default 25)")
    ap.add_argument("-s", "--seed", type=int, default=1337,
                    help="RNG seed for reproducible output (default 1337)")
    ap.add_argument("-o", "--outdir", default="seed_output",
                    help="output directory (default ./seed_output)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    data = build_all(args.count, args.seed)

    results = [
        write_mongodb_file(data["mongodb"], args.outdir),
        write_elasticsearch_file(data["elasticsearch"], args.outdir),
        write_cassandra_file(data["cassandra"], args.outdir),
        write_redis_file(data["redis"], args.outdir),
        write_couchdb_file(data["couchdb"], args.outdir),
        write_hadoop_file(data["hadoop"], args.outdir),
    ]

    with open(os.path.join(args.outdir, "hipaa_identifier_map.json"), "w") as f:
        json.dump(HIPAA_IDENTIFIER_MAP, f, indent=2)
    with open(os.path.join(args.outdir, "_manifest.json"), "w") as f:
        json.dump({
            "generator": "faker",
            "seed": args.seed,
            "patient_count": args.count,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "classification": CLASSIFICATION,
        }, f, indent=2)

    print(f"\n  Generated {args.count} patients (seed={args.seed}) -> {args.outdir}/\n")
    for path, count in results:
        print(f"    {os.path.relpath(path, args.outdir):24s}  {count} records")
    print("    hipaa_identifier_map.json  (18-identifier map)")
    print("    _manifest.json             (reproducibility manifest)\n")


if __name__ == "__main__":
    main()