import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import bcrypt
import json

from db_connection import MongoDBConnection

@dataclass
class BaseUser(ABC):
    username: str
    password_hash: str
    password_salt: str
    last_login: datetime
    api_endpoints: List[str] = field(default_factory=list)
    _id: str = field(default_factory=lambda: f"USER-{uuid.uuid4()}")

    # Collection name for MongoDB
    COLLECTION_NAME: str = "users"

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
            "api_endpoints": self.api_endpoints
        }

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
        return json.dumps({
            "id": self._id,
            "username": self.username,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S"),
            "api_endpoints": self.api_endpoints
        }, indent=4)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseUser):
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
                            "bsonType": "date",
                            "description": "must be a date and is required"
                        },
                        "api_endpoints": {
                            "bsonType": "array",
                            "description": "must be an array of strings",
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
    def db_drop_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for users.
        """
        db_connection.db.drop_collection(cls.COLLECTION_NAME)

    def db_save(self, db_connection: MongoDBConnection) -> None:
        """
        Save the user object to MongoDB.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @staticmethod
    def _db_load(data: dict) -> 'BaseUser':
        """
        Load a User object from a dictionary (as retrieved from MongoDB).
        """
        return BaseUser(
            username=data.get("username"),
            password_hash=data.get("password_hash"),
            password_salt=data.get("password_salt"),
            last_login=data.get("last_login"),
            api_endpoints=data.get("api_endpoints", []),
            _id=data.get("_id")
        )

    @classmethod
    def db_find(cls, db_connection: MongoDBConnection, _id: str) -> Optional['BaseUser']:
        """
        Find a User object in the database by _id.
        Returns a User instance if found, else None.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return cls._db_load(data)
        return None

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
    def db_find_all(cls, db_connection: MongoDBConnection) -> List['BaseUser']:
        """
        Retrieve all User objects from the database.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        docs = collection.find()
        return [cls._db_load(doc) for doc in docs]
