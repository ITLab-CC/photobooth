
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Tuple

import bcrypt

from img_server.db_connection import MongoDBConnection, mongodb_get_user_permissions
from img_server.role import Role

# Helper functions to convert datetime objects to/from strings.
def datetime_to_str(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None

def datetime_from_str(dt_str: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(dt_str) if dt_str else None

# Define a module-level constant for the collection name.
USERS_COLLECTION = "users"

@dataclass
class User:
    username: str
    password_hash: str
    password_salt: str
    last_login: Optional[datetime] = None
    roles: List[str] = field(default_factory=list)
    _id: str = field(default_factory=lambda: f"USER-{uuid.uuid4()}")

    # Collection name for MongoDB.
    COLLECTION_NAME: str = USERS_COLLECTION

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """Convert the object to a dictionary."""
        return {
            "_id": self._id,
            "username": self.username,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "roles": self.roles
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Rebuild a User object from a dictionary.
        Note: expects that any datetime fields have been encoded as ISO strings.
        """
        last_login = data.get("last_login")
        if last_login:
            last_login = datetime.fromisoformat(last_login)
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            password_salt=data["password_salt"],
            last_login=last_login,
            roles=data.get("roles", []),
            _id=data["_id"]
        )

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
        return json.dumps({
            "id": self._id,
            "username": self.username,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S") if self.last_login else None,
            "roles": self.roles
        }, indent=4)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, User):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def db_create_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Create the MongoDB collection for users with validation.
        """
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "username", "password_hash", "password_salt", "last_login"],
                    "properties": {
                        "_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the user, required and acts as primary key"
                        },
                        "username": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "password_hash": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "password_salt": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "last_login": {
                            "bsonType": ["string", "null"],
                            "description": "must be a string as ISO date or null"
                        },
                        "roles": {
                            "bsonType": "array",
                            "description": "must be an array and is required",
                            "items": {
                                "bsonType": "string"
                            }
                        }
                    }
                }
            },
            "validationLevel": "strict",
            "validationAction": "error"
        }
        if cls.COLLECTION_NAME not in db_connection.db.list_collection_names():
            db_connection.db.create_collection(
                name=cls.COLLECTION_NAME,
                validator=schema["validator"],
                validationLevel=schema["validationLevel"],
                validationAction=schema["validationAction"]
            )

            #create db.collection.createIndex({ "username": 1 }, { unique: true })
            db_connection.db[cls.COLLECTION_NAME].create_index([("username", 1)], unique=True)

    @classmethod
    def db_drop_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for users.
        """
        db_connection.db.drop_collection(cls.COLLECTION_NAME)

    @classmethod
    def new(cls, db_connection: MongoDBConnection, username: str, password: str, roles: List[str] = None) -> "User":
        """
        Create a new user in the database.
        """

        if roles is None:
            roles = []

        # Check if the username already exists
        existing_user = User.db_find_by_username(db_connection, username)
        if existing_user:
            raise ValueError(f"Username '{username}' already exists.")
        
        # check if role exists
        db_roles = Role.db_find_all(db_connection)
        for role in roles:
            if role not in [r for r in db_roles]:
                raise ValueError(f"Role '{role}' does not exist.")

        # Hash the password and generate a salt
        password_hash, password_salt = User.hash_password(password)

        # Create a new user instance
        new_user = User(
            username=username,
            password_hash=password_hash,
            password_salt=password_salt,
            roles=roles
        )

        # Save the new user to the database
        new_user.db_save(db_connection)
        return new_user

    def db_save(self, db_connection: MongoDBConnection) -> None:
        """
        Save the user object to MongoDB.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @classmethod
    def db_find_by_id(cls, db_connection: MongoDBConnection, _id: str) -> Optional['User']:
        """
        Find a User object in the database by _id.
        Returns a User instance if found, else None.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return cls._db_load(data)
        return None
    
    @classmethod
    def db_find_by_username(cls, db_connection: MongoDBConnection, username: str) -> Optional['User']:
        """
        Find a User object in the database by username.
        Returns a User instance if found, else None.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        data = collection.find_one({"username": username})
        if data:
            return cls._db_load(data)
        return None

    def db_refresh(self, db_connection: MongoDBConnection) -> None:
        """
        Refresh the current User instance with the latest data from the database.

        This method retrieves the document from MongoDB using the user's _id and
        updates the instance's attributes accordingly.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        # Look up the user document in the database by _id.
        data = collection.find_one({"_id": self._id})
        if data:
            # Use the _db_load helper to create a temporary instance with new data.
            refreshed_user = self.__class__._db_load(data)
            # Update the current instance's attributes with the refreshed data.
            self.username = refreshed_user.username
            self.password_hash = refreshed_user.password_hash
            self.password_salt = refreshed_user.password_salt
            self.last_login = refreshed_user.last_login
            self.roles = refreshed_user.roles
        else:
            raise ValueError(f"User with id {self._id} not found in the database.")


    def db_update(self, db_connection: MongoDBConnection) -> None:
        """
        Update the User object in the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.update_one({"_id": self._id}, {"$set": data})

    def db_delete(self, db_connection: MongoDBConnection) -> None:
        """
        Delete the User object from the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})

    @classmethod
    def db_find_all(cls, db_connection: MongoDBConnection) -> List['User']:
        """
        Retrieve all User objects from the database.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        docs = collection.find()
        return [cls._db_load(doc) for doc in docs]

    @classmethod
    def _db_load(cls, data: dict) -> 'User':
        """Convert a MongoDB document into a User instance."""
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            password_salt=data["password_salt"],
            last_login=data["last_login"],
            roles=[str(role) for role in data.get("roles", [])],
            _id=data["_id"]
        )

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash the given password using bcrypt. Generates a new salt if not provided.
        Returns a tuple of (hashed_password, salt).
        """
        if salt is None:
            salt_bytes = bcrypt.gensalt()
            salt = salt_bytes.decode()
        hashed = bcrypt.hashpw(password.encode(), salt.encode()).decode()
        return hashed, salt


def main() -> None:
    MONGODB_URI = "localhost:27017"
    MONGODB_ADMIN_USER = "admin"
    MONGODB_ADMIN_PASSWORD = "admin"
    MONGODB_DB_NAME = "photo_booth"

    admin_db = MongoDBConnection(
        mongo_uri=MONGODB_URI,
        user=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        db_name=MONGODB_DB_NAME,
        admin=True
    )

    User.db_drop_collection(admin_db)
    User.db_create_collection(admin_db)

    # Create a new user
    new_user = User.new(
        db_connection=admin_db,
        username="testuser",
        password="password123",
        roles=["admin"]
    )

    # Retrieve the user by username
    retrieved_user = User.db_find_by_username(admin_db, "testuser")
    if retrieved_user:
        print(f"Retrieved User: {retrieved_user}")
    else:
        print("User not found.")

    # Update the user
    retrieved_user.roles.append("editor")
    retrieved_user.db_update(admin_db)
    print(f"Updated User: {retrieved_user}")

    # Retrieve all users
    all_users = User.db_find_all(admin_db)
    print("All Users:")
    for user in all_users:
        print(user)

    # Delete the user
    retrieved_user.db_delete(admin_db)
    print("User deleted.")

    # Verify deletion
    deleted_user = User.db_find_by_username(admin_db, "testuser")
    if deleted_user:
        print(f"User still exists: {deleted_user}")
    else:
        print("User successfully deleted.")

    # Drop the collection
    User.db_drop_collection(admin_db)
    print("Collection dropped.")
    # Close the database connection
    admin_db.close()

if __name__ == "__main__":
    main()
