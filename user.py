
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from db_connection import MongoDBConnection, MongoDBPermissions, mongodb_permissions, mongodb_get_user_permissions

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
            "last_login": self.last_login,
            "roles": self.roles
        }

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
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.CREATE_COLLECTION], roles=["boss"])
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
                            "bsonType": ["date", "null"],
                            "description": "must be a date and is required"
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

    @classmethod
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.DROP_COLLECTION], roles=["boss"])
    def db_drop_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for users.
        """
        db_connection.db.drop_collection(cls.COLLECTION_NAME)

    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.INSERT], roles=["boss"])
    def db_save(self, db_connection: MongoDBConnection) -> None:
        """
        Save the user object to MongoDB.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @classmethod
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "login_manager"])
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
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "login_manager"])
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

    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=["boss", "login_manager"])
    def db_update(self, db_connection: MongoDBConnection) -> None:
        """
        Update the User object in the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.update_one({"_id": self._id}, {"$set": data})

    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.REMOVE], roles=["boss"])
    def db_delete(self, db_connection: MongoDBConnection) -> None:
        """
        Delete the User object from the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})

    @classmethod
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "login_manager"])
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

def main() -> None:
    MONGODB_URI = "localhost:27017"
    MONGODB_ADMIN_USER = "root"
    MONGODB_ADMIN_PASSWORD = "example"
    MONGODB_DB_NAME = "photo_booth"

    admin_db = MongoDBConnection(
        mongo_uri=MONGODB_URI,
        user=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        db_name=MONGODB_DB_NAME
    )

    User.db_drop_collection(admin_db)
    User.db_create_collection(admin_db)

    roles = mongodb_get_user_permissions(User, MONGODB_DB_NAME, ["boss"])
    print(roles)

    def role_exists(admin_db: MongoDBConnection, role_name: str) -> bool:
        """Check if a role already exists in MongoDB."""
        roles_info = admin_db.db.command("rolesInfo", role_name)
        roles_list = roles_info.get("roles", [])
        return any(role.get("role") == role_name for role in roles_list)

    def remove_role(admin_db: MongoDBConnection, role_name: str) -> None:
        """Remove an existing role if it exists."""
        if role_exists(admin_db, role_name):
            admin_db.db.command("dropRole", role_name)

    # When removing/creating roles via db commands, use the enum's value.
    remove_role(admin_db, "boss")
    admin_db.db.command("createRole", "boss", privileges=roles, roles=[])
    print("Role created")

    # print role
    print(admin_db.db.command("rolesInfo", "boss", showPrivileges=True))

if __name__ == "__main__":
    main()
