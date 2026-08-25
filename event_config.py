from dataclasses import dataclass, field
import json
from typing import Optional

from db_connection import MongoDBConnection, MongoDBPermissions, mongodb_permissions

# Define a module-level constant for the collection name.
EVENT_CONFIG_COLLECTION = "event_config"

# Singleton document id: this collection only ever holds one document.
EVENT_CONFIG_ID = "CONFIG-default"


@dataclass
class EventConfig:
    title: str
    subtitle: str
    brand_name: str
    pin_fail_redirect_url: str
    _id: str = field(default=EVENT_CONFIG_ID)

    # Collection name for MongoDB.
    COLLECTION_NAME: str = EVENT_CONFIG_COLLECTION

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """Convert the object to a dictionary."""
        return {
            "_id": self._id,
            "title": self.title,
            "subtitle": self.subtitle,
            "brand_name": self.brand_name,
            "pin_fail_redirect_url": self.pin_fail_redirect_url,
        }

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
        return json.dumps(self.to_dict(), indent=4)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EventConfig):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    @mongodb_permissions(collection=EVENT_CONFIG_COLLECTION, actions=[MongoDBPermissions.CREATE_COLLECTION], roles=["boss"])
    def db_create_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Create the MongoDB collection for event config with validation.
        """
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "title", "subtitle", "brand_name", "pin_fail_redirect_url"],
                    "properties": {
                        "_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the event config, required and acts as primary key"
                        },
                        "title": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "subtitle": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "brand_name": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "pin_fail_redirect_url": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
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
    @mongodb_permissions(collection=EVENT_CONFIG_COLLECTION, actions=[MongoDBPermissions.DROP_COLLECTION], roles=["boss"])
    def db_drop_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for event config.
        """
        db_connection.db.drop_collection(cls.COLLECTION_NAME)

    @mongodb_permissions(collection=EVENT_CONFIG_COLLECTION, actions=[MongoDBPermissions.INSERT], roles=["boss"])
    def db_save(self, db_connection: MongoDBConnection) -> None:
        """
        Save the EventConfig object to MongoDB.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @mongodb_permissions(collection=EVENT_CONFIG_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=["boss"])
    def db_update(self, db_connection: MongoDBConnection) -> None:
        """
        Update the EventConfig object in the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.update_one({"_id": self._id}, {"$set": data})

    @classmethod
    @mongodb_permissions(collection=EVENT_CONFIG_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "photo_booth"])
    def db_find(cls, db_connection: MongoDBConnection) -> Optional['EventConfig']:
        """
        Find the singleton EventConfig document in the database.
        Returns an EventConfig instance if found, else None.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": EVENT_CONFIG_ID})
        if data:
            return cls._db_load(data)
        return None

    @classmethod
    def _db_load(cls, data: dict) -> 'EventConfig':
        """Convert a MongoDB document into an EventConfig instance."""
        return cls(
            title=data["title"],
            subtitle=data["subtitle"],
            brand_name=data["brand_name"],
            pin_fail_redirect_url=data["pin_fail_redirect_url"],
            _id=str(data.get("_id", EVENT_CONFIG_ID)),
        )
