-- Create keyspace (equivalent to database)
CREATE KEYSPACE IF NOT EXISTS my_keyspace
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- Use the keyspace
USE my_keyspace;

-- Create table (equivalent to collection)
CREATE TABLE IF NOT EXISTS my_table (
    id TEXT PRIMARY KEY,
    firstName TEXT,
    lastName TEXT,
    email TEXT,
    phoneNumber TEXT
);

-- Insert sample data
INSERT INTO my_table (id, firstName, lastName, email, phoneNumber)
VALUES ('1', 'John', 'Doe', 'john@doe.com', '0123456789');

INSERT INTO my_table (id, firstName, lastName, email, phoneNumber)
VALUES ('2', 'Jane', 'Doe', 'jane@doe.com', '9876543210');

INSERT INTO my_table (id, firstName, lastName, email, phoneNumber)
VALUES ('3', 'James', 'Bond', 'james.bond@mi6.co.uk', '0612345678');
