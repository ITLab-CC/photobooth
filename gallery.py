from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import uuid
import json


from db_connection import MongoDBConnection

@dataclass
class Gallery:
    creation_time: datetime
    expiration_time: datetime
    images: List[str] = field(default_factory=list)
    _id: str = field(default_factory=lambda: f"GAL-{uuid.uuid4()}")

    # Collection name for MongoDB
    COLLECTION_NAME: str = "galleries"

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """Convert the object to a dictionary."""
        return {
            "_id": self._id,  # MongoDB expects the primary key field to be '_id'
            "creation_time": self.creation_time,
            "expiration_time": self.expiration_time,
            "images": self.images
        }

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
        return json.dumps({
            "id": self._id,
            "creation_time": self.creation_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expiration_time": self.expiration_time.strftime("%Y-%m-%d %H:%M:%S"),
            "images": self.images
        }, indent=4)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, Gallery):
            return self.id == o.id
        return False
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    @staticmethod
    def db_create_collection(db_c: MongoDBConnection) -> None:
        """
        Create the MongoDB collection for galleries with validation.
        """
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "creation_time", "expiration_time"],
                    "properties": {
                        "_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the gallery, required and acts as primary key"
                        },
                        "creation_time": {
                            "bsonType": "date",
                            "description": "The time the gallery was created"
                        },
                        "expiration_time": {
                            "bsonType": "date",
                            "description": "The time the gallery will be deleted"
                        },
                        "images": {
                            "bsonType": "array",
                            "description": "List of image IDs in the gallery",
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

        # Get existing collections
        collections = db_c.db.list_collection_names()
        if Gallery.COLLECTION_NAME in collections:
            # skip
            return

        db_c.db.create_collection(
            name=Gallery.COLLECTION_NAME,
            validator=schema["validator"],
            validationLevel=schema["validationLevel"],
            validationAction=schema["validationAction"]
        )

    @staticmethod
    def db_drop_collection(db_c: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for galleries.
        """
        db_c.db.drop_collection(Gallery.COLLECTION_NAME)

    def db_save(self, db_c: MongoDBConnection) -> None:
        """
        Save the Gallery object to MongoDB.
        """
        collection = db_c.db[Gallery.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @staticmethod
    def _db_load(data: dict) -> 'Gallery':
        """
        Load a Gallery object from a dictionary (as retrieved from MongoDB).
        """
        return Gallery(
            creation_time=data.get("creation_time"),
            expiration_time=data.get("expiration_time"),
            images=data.get("images", []),
            _id=data.get("_id")
        )

    @staticmethod
    def db_find(db_c: MongoDBConnection, _id: str) -> Optional['Gallery']:
        """
        Find a Gallery object in the database by _id.
        Returns a Gallery instance if found, else None.
        """
        collection = db_c.db[Gallery.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return Gallery._db_load(data)
        return None

    def db_update(self, db_c: MongoDBConnection) -> None:
        """
        Update the Gallery object in the database.
        """
        collection = db_c.db[Gallery.COLLECTION_NAME]
        data = self.to_dict()
        collection.update_one({"_id": self._id}, {"$set": data})

    def db_delete(self, db_c: MongoDBConnection) -> None:
        """
        Delete the Gallery object from the database.
        """
        collection = db_c.db[Gallery.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})

    @staticmethod
    def db_find_all(db_c: MongoDBConnection) -> List['Gallery']:
        """
        Retrieve all Gallery objects from the database.
        """
        collection = db_c.db[Gallery.COLLECTION_NAME]
        docs = collection.find()
        return [Gallery._db_load(doc) for doc in docs]
