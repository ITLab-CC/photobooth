import uuid
import json
import dataclasses
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum

from img_server.db_connection import MongoDBConnection

ROLES_COLLECTION = "roles"

class Method(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    ANY = "ANY"

@dataclass
class Endpoint:
    method: Method
    path_filter: str

    def to_dict(self) -> dict:
        """
        Convert an Endpoint instance to a dictionary.
        The enum 'method' is converted to its string value.
        """
        return {
            "method": self.method.value,
            "path_filter": self.path_filter
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Endpoint":
        """
        Create an Endpoint instance from a dictionary.
        The 'method' string is converted back into a 'method' enum.
        """
        return cls(
            method=Method(data["method"]),
            path_filter=data["path_filter"]
        )

@dataclass
class Role:
    rolename: str
    api_endpoints: List[Endpoint] = field(default_factory=list)
    _id: str = field(default_factory=lambda: f"ROLE-{uuid.uuid4()}")

    # Collection name for MongoDB.
    COLLECTION_NAME: str = ROLES_COLLECTION

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """Convert the Role object to a dictionary."""
        return {
            "_id": self._id,
            "rolename": self.rolename,
            # Use the custom Endpoint.to_dict method instead of dataclasses.asdict.
            "api_endpoints": [endpoint.to_dict() for endpoint in self.api_endpoints],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Role":
        """Rebuild a Role object from a dictionary."""
        return cls(
            rolename=data["rolename"],
            # Deserialize each dictionary into an Endpoint using the custom from_dict.
            api_endpoints=[Endpoint.from_dict(ep) for ep in data.get("api_endpoints", [])],
            _id=data["_id"]
        )

    def __str__(self) -> str:
        """Return a JSON representation of the Role object."""
        return json.dumps({
            "id": self._id,
            "rolename": self.rolename,
            "api_endpoints": [endpoint.to_dict() for endpoint in self.api_endpoints],
        }, indent=4)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def db_create_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Create the MongoDB collection for roles with validation.
        """
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "rolename", "api_endpoints"],
                    "properties": {
                        "_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the role, required and acts as primary key"
                        },
                        "rolename": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "api_endpoints": {
                            "bsonType": "array",
                            "description": "must be an array and is required",
                            "items": {
                                "bsonType": "object",
                                "required": ["method", "path_filter"],
                                "properties": {
                                    "method": {
                                        "bsonType": "string",
                                        "description": "HTTP method for the endpoint"
                                    },
                                    "path_filter": {
                                        "bsonType": "string",
                                        "description": "Path filter for the endpoint"
                                    }
                                }
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
            # Create an index on rolename to enforce uniqueness if desired.
            db_connection.db[cls.COLLECTION_NAME].create_index([("rolename", 1)], unique=True)

    @classmethod
    def db_drop_collection(cls, db_connection: MongoDBConnection) -> None:
        """Drop the MongoDB collection for roles."""
        db_connection.db.drop_collection(cls.COLLECTION_NAME)

    def db_save(self, db_connection: MongoDBConnection) -> None:
        """Save the Role object to MongoDB."""
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @classmethod
    def new(cls, db_connection: MongoDBConnection, rolename: str, api_endpoints: List[Endpoint]) -> "Role":
        """
        Create a new Role object and save it to the database.
        :param db_connection: MongoDBConnection instance
        :param rolename: Name of the role
        :param api_endpoints: List of Endpoint objects
        :return: Role object
        """
        role = cls(rolename=rolename, api_endpoints=api_endpoints)
        role.db_save(db_connection)
        return role

    @classmethod
    def db_find_by_id(cls, db_connection: MongoDBConnection, _id: str) -> Optional["Role"]:
        """
        Find a Role object in the database by _id.
        Returns a Role instance if found, else None.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return cls._db_load(data)
        return None

    @classmethod
    def db_find_by_rolename(cls, db_connection: MongoDBConnection, rolename: str) -> Optional["Role"]:
        """
        Find a Role object in the database by name.
        Returns a Role instance if found, else None.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        data = collection.find_one({"rolename": rolename})
        if data:
            return cls._db_load(data)
        return None

    def db_refresh(self, db_connection: MongoDBConnection) -> None:
        """
        Refresh the current Role instance with the latest data from the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = collection.find_one({"_id": self._id})
        if data:
            refreshed_role = self.__class__._db_load(data)
            self.rolename = refreshed_role.rolename
            self.api_endpoints = refreshed_role.api_endpoints
        else:
            raise ValueError(f"Role with id {self._id} not found in the database.")

    def db_update(self, db_connection: MongoDBConnection) -> None:
        """Update the Role object in the database."""
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.update_one({"_id": self._id}, {"$set": data})

    def db_delete(self, db_connection: MongoDBConnection) -> None:
        """Delete the Role object from the database."""
        collection = db_connection.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})

    @classmethod
    def db_delete_by_id(cls, db_connection: MongoDBConnection, _id: str) -> None:
        """Delete a Role object from the database by _id."""
        collection = db_connection.db[cls.COLLECTION_NAME]
        collection.delete_one({"_id": _id})

    @classmethod
    def db_find_all(cls, db_connection: MongoDBConnection) -> Dict[str, "Role"]:
        """
        Retrieve all Role objects from the database.
        Returns a dictionary with role id as key and Role instance as value.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        docs = collection.find()
        roles_list = [cls._db_load(doc) for doc in docs]
        roles_dict = {role.id: role for role in roles_list}
        return roles_dict


    @classmethod
    def _db_load(cls, data: dict) -> "Role":
        """Convert a MongoDB document into a Role instance."""
        return cls(
            rolename=data["rolename"],
            api_endpoints=[Endpoint.from_dict(ep) for ep in data.get("api_endpoints", [])],
            _id=data["_id"]
        )
