import base64
from dataclasses import dataclass, field
import io
from typing import Optional, List
from PIL import Image
import uuid
import json
from io import BytesIO

from pymongo.collection import Collection

from db_connection import MongoDBConnection, MongoDBPermissions, mongodb_permissions

# Define a module-level constant for the collection name.
BACKGROUND_COLLECTION = "backgrounds"

@dataclass
class Background:
    img: Image.Image
    _id: str = field(default_factory=lambda: f"Back-{uuid.uuid4()}")

    # Collection name for MongoDB
    COLLECTION_NAME: str = BACKGROUND_COLLECTION

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """
        Convert the object to a dictionary.
        Note: The 'img' field remains a PIL Image here and is converted to bytes
        when saving to the database.
        """
        return {
            "_id": self._id,  # MongoDB uses _id as the primary key.
            "img": self.img,  # Convert to binary data before saving.
        }

    def __str__(self) -> str:
        """
        Return a JSON representation of the object.
        (For the image, only the size and mode are shown.)
        """
        return json.dumps({
            "id": self._id,
            "img": {
                "size": self.img.size,
                "mode": self.img.mode
            }
        }, indent=4)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, Background):
            return self.id == o.id
        return False
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    @classmethod
    @mongodb_permissions(collection=BACKGROUND_COLLECTION, actions=[MongoDBPermissions.CREATE_COLLECTION], roles=["boss"])
    def db_create_collection(cls, db_c: MongoDBConnection) -> None:
        """
        Create the MongoDB collection for images with validation.
        """
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "img"],
                    "properties": {
                        "_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the image, required and acts as primary key"
                        },
                        "img": {
                            "bsonType": "binData",
                            "description": "Image data stored as binary"
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

    @classmethod
    @mongodb_permissions(collection=BACKGROUND_COLLECTION, actions=[MongoDBPermissions.DROP_COLLECTION], roles=["boss"])
    def db_drop_collection(cls, db_c: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for images.
        """
        db_c.db.drop_collection(cls.COLLECTION_NAME)
    
    @classmethod
    def _image_to_bytes(cls, img: Image.Image, format: str = "PNG") -> bytes:
        """
        Convert a PIL Image to bytes.
        """
        with BytesIO() as output:
            img.save(output, format=format)
            return output.getvalue()

    @classmethod
    def _bytes_to_image(cls, data: bytes) -> Image.Image:
        """
        Convert bytes data to a PIL Image.
        """
        return Image.open(BytesIO(data))
    
    @staticmethod
    def from_base64(base64_str: str) -> 'Background':
        """
        Create an Background object from a base64 string.
        """
        try:
            image_bytes = base64.b64decode(base64_str)
            image_file = io.BytesIO(image_bytes)
            pil_image = Image.open(image_file).convert("RGBA")
        except Exception:
            raise ValueError("Invalid base64 string; cannot convert to image.")
        
        return Background(img=pil_image)


    @classmethod
    def _db_load(cls, data: dict) -> 'Background':
        """
        Load an Background object from a dictionary (as retrieved from MongoDB).
        Converts the stored binary data back into a PIL Image.
        """
        img_data = data.get("img")
        
        if img_data is None:
            raise ValueError("Image data is missing from the database entry.")

        # Ensure the image data is in bytes (in case it comes as a different binary type)
        if not isinstance(img_data, bytes):
            try:
                img_data = bytes(img_data)
            except TypeError:
                raise ValueError("Invalid image data format; cannot convert to bytes.")

        image = cls._bytes_to_image(img_data)
        
        return cls(
            img=image,
            _id=str(data.get("_id"))
        )

    @mongodb_permissions(collection=BACKGROUND_COLLECTION, actions=[MongoDBPermissions.INSERT], roles=["boss"])
    def db_save(self, db_c: MongoDBConnection) -> None:
        """
        Save the Background object to MongoDB.
        Converts the PIL Image to binary data before insertion.
        """
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        data = self.to_dict()
        data["img"] = self._image_to_bytes(self.img)
        collection.insert_one(data)
    
    @classmethod
    @mongodb_permissions(collection=BACKGROUND_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "photo_booth", "img_viewer"])
    def db_find(cls, db_c: MongoDBConnection, _id: str) -> Optional['Background']:
        """
        Find the Background object in the database by _id.
        Returns an Background instance if found, else None.
        """
        collection: Collection = db_c.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return cls._db_load(data)
        return None
    
    @mongodb_permissions(collection=BACKGROUND_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=["boss"])
    def db_update(self, db_c: MongoDBConnection) -> None:
        """
        Update the Background object in the database.
        """
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        data = self.to_dict()
        data["img"] = self._image_to_bytes(self.img)
        collection.update_one({"_id": self._id}, {"$set": data})
    
    @mongodb_permissions(collection=BACKGROUND_COLLECTION, actions=[MongoDBPermissions.REMOVE], roles=["boss"])
    def db_delete(self, db_c: MongoDBConnection) -> None:
        """
        Delete the Background object from the database.
        """
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})
    
    @classmethod
    @mongodb_permissions(collection=BACKGROUND_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "photo_booth", "img_viewer"])
    def db_find_all(cls, db_c: MongoDBConnection) -> List['Background']:
        """
        Find all Background objects in the database.
        Returns a list of Background instances.
        """
        collection: Collection = db_c.db[cls.COLLECTION_NAME]
        docs = collection.find()
        return [cls._db_load(doc) for doc in docs]