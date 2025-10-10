db = db.getSiblingDB('my_database');

db.my_table.insertMany([
  {
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@doe.com",
    "phoneNumber": "0123456789"
  },
  {
    "firstName": "Jane",
    "lastName": "Doe",
    "email": "jane@doe.com",
    "phoneNumber": "9876543210" 
  },
  {
    "firstName": "James",
    "lastName": "Bond",
    "email": "james.bond@mi6.co.uk",
    "phoneNumber": "0612345678" 
  }
]);
