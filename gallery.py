from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime
import uuid
import json

import bcrypt


from db_connection import MongoDBConnection, MongoDBPermissions, mongodb_permissions

# Define a module-level constant for the collection name.
GALLERY_COLLECTION = "galleries"

@dataclass
class Gallery:
    creation_time: datetime
    expiration_time: datetime
    images: List[str] = field(default_factory=list)
    pin_hash: Optional[str] = None
    pin_salt: Optional[str] = None
    _id: str = field(default_factory=lambda: f"GAL-{uuid.uuid4()}")

    # Collection name for MongoDB
    COLLECTION_NAME: str = GALLERY_COLLECTION

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """Convert the object to a dictionary."""
        return {
            "_id": self._id,  # MongoDB expects the primary key field to be '_id'
            "creation_time": self.creation_time,
            "expiration_time": self.expiration_time,
            "images": self.images,
            "pin_hash": self.pin_hash,
            "pin_salt": self.pin_salt
        }

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
        return json.dumps({
            "id": self._id,
            "creation_time": self.creation_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expiration_time": self.expiration_time.strftime("%Y-%m-%d %H:%M:%S"),
            "images": self.images,
            "pin_hash": self.pin_hash,
            "pin_salt": self.pin_salt
        }, indent=4)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, Gallery):
            return self.id == o.id
        return False
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    @classmethod
    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.CREATE_COLLECTION], roles=["boss"])
    def db_create_collection(cls, db_c: MongoDBConnection) -> None:
        """
        Create the MongoDB collection for galleries with validation.
        """
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "creation_time", "expiration_time", "images", "pin_hash", "pin_salt"],
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
                        },
                        "pin_hash": {
                            "bsonType": ["string", "null"],
                            "description": "Hash of the PIN for the gallery"
                        },
                        "pin_salt": {
                            "bsonType": ["string", "null"],
                            "description": "Salt used to hash the PIN"
                        }
                    }
                }
            },
            "validationLevel": "strict",
            "validationAction": "error"
        }

        # Get existing collections
        collections = db_c.db.list_collection_names()
        if cls.COLLECTION_NAME in collections:
            # skip
            return

        db_c.db.create_collection(
            name=cls.COLLECTION_NAME,
            validator=schema["validator"],
            validationLevel=schema["validationLevel"],
            validationAction=schema["validationAction"]
        )

    @staticmethod
    def hash_pin(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash the given password using bcrypt. Generates a new salt if not provided.
        Returns a tuple of (hashed_password, salt).
        """
        if salt is None:
            salt_bytes = bcrypt.gensalt()
            salt = salt_bytes.decode()
        hashed = bcrypt.hashpw(password.encode(), salt.encode()).decode()
        return hashed, salt

    @classmethod
    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.DROP_COLLECTION], roles=["boss"])
    def db_drop_collection(cls, db_c: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for galleries.
        """
        db_c.db.drop_collection(cls.COLLECTION_NAME)

    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.INSERT], roles=["boss", "photo_booth"])
    def db_save(self, db_c: MongoDBConnection) -> None:
        """
        Save the Gallery object to MongoDB.
        """
        collection = db_c.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @classmethod
    def _db_load(cls, data: dict) -> 'Gallery':
        """
        Load a Gallery object from a dictionary (as retrieved from MongoDB).
        Ensures that 'creation_time' and 'expiration_time' are converted to datetime.
        """
        creation_time_raw = data.get("creation_time")
        expiration_time_raw = data.get("expiration_time")

        # Ensure proper datetime conversion
        creation_time = (
            datetime.fromisoformat(creation_time_raw)
            if isinstance(creation_time_raw, str)
            else creation_time_raw
        ) or datetime.now()  # Default to now if None

        expiration_time = (
            datetime.fromisoformat(expiration_time_raw)
            if isinstance(expiration_time_raw, str)
            else expiration_time_raw
        ) or datetime.now()  # Default to now if None

        pin_hash = data.get("pin_hash")
        pin_salt = data.get("pin_salt")

        _id = str(data.get("_id")) if data.get("_id") is not None else f"GAL-{uuid.uuid4()}"

        return Gallery(
            creation_time=creation_time,
            expiration_time=expiration_time,
            images=data.get("images", []),
            _id=_id,
            pin_hash=pin_hash,
            pin_salt=pin_salt
        )



    @classmethod
    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "photo_booth", "img_viewer", "old_img_eraser"])
    def db_find(cls, db_c: MongoDBConnection, _id: str) -> Optional['Gallery']:
        """
        Find a Gallery object in the database by _id.
        Returns a Gallery instance if found, else None.
        """
        collection = db_c.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return cls._db_load(data)
        return None

    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=["boss"])
    def db_update(self, db_c: MongoDBConnection) -> None:
        """
        Update the Gallery object in the database.
        """
        collection = db_c.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.update_one({"_id": self._id}, {"$set": data})

    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=["boss", "photo_booth"])
    def db_set_pin(self, db_c: MongoDBConnection, pin: Optional[str]) -> None:
        """
        Set a PIN for the gallery. Hashes the PIN and stores the hash and salt.
        """
        pin_hash = None
        pin_salt = None
        if pin is None:
            self.pin_hash = None
            self.pin_salt = None
        else:
            pin_hash, pin_salt = self.hash_pin(pin)
            self.pin_hash = pin_hash
            self.pin_salt = pin_salt
        
        collection = db_c.db[self.COLLECTION_NAME]
        collection.update_one({"_id": self._id}, {"$set": {"pin_hash": pin_hash, "pin_salt": pin_salt}})

    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=["boss", "photo_booth"])
    def db_add_image(self, db_c: MongoDBConnection, img_id: str) -> None:
        """
        Add an image to the gallery.
        """
        self.images.append(img_id)
        collection = db_c.db[self.COLLECTION_NAME]
        collection.update_one({"_id": self._id}, {"$set": {"images": self.images}})

    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=["boss"])
    def db_remove_image(self, db_c: MongoDBConnection, img_id: str) -> None:
        """
        Remove an image from the gallery.
        """
        self.images.remove(img_id)
        collection = db_c.db[self.COLLECTION_NAME]
        collection.update_one({"_id": self._id}, {"$set": {"images": self.images}})

    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.REMOVE], roles=["boss", "old_img_eraser"])
    def db_delete(self, db_c: MongoDBConnection) -> None:
        """
        Delete the Gallery object from the database.
        """
        collection = db_c.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})

    @classmethod
    @mongodb_permissions(collection=GALLERY_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "img_viewer"])
    def db_find_all(cls, db_c: MongoDBConnection) -> List['Gallery']:
        """
        Retrieve all Gallery objects from the database.
        """
        collection = db_c.db[cls.COLLECTION_NAME]
        docs = collection.find()
        return [cls._db_load(doc) for doc in docs]
