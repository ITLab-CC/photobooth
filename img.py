from dataclasses import dataclass, field
from typing import Optional, List
from PIL import Image
import uuid
import json
from io import BytesIO

from pymongo.collection import Collection

from db_connection import MongoDBConnection

@dataclass
class IMG:
    img: Image.Image
    name: str
    description: str
    gallery: Optional[str] = None
    _id: str = field(default_factory=lambda: f"IMG-{uuid.uuid4()}")

    # Collection name for MongoDB
    COLLECTION_NAME: str = "images"

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
            "name": self.name,
            "description": self.description,
            "img": self.img,  # Convert to binary data before saving.
            "gallery": self.gallery
        }

    def __str__(self) -> str:
        """
        Return a JSON representation of the object.
        (For the image, only the size and mode are shown.)
        """
        return json.dumps({
            "id": self._id,
            "name": self.name,
            "description": self.description,
            "gallery": self.gallery,
            "img": {
                "size": self.img.size,
                "mode": self.img.mode
            }
        }, indent=4)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, IMG):
            return self.id == o.id
        return False
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    @staticmethod
    def db_create_collection(db_c: MongoDBConnection) -> None:
        """
        Create the MongoDB collection for images with validation.
        """
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "img", "name", "description"],
                    "properties": {
                        "_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the image, required and acts as primary key"
                        },
                        "img": {
                            "bsonType": "binData",
                            "description": "Image data stored as binary"
                        },
                        "name": {
                            "bsonType": "string",
                            "description": "Name of the image"
                        },
                        "description": {
                            "bsonType": "string",
                            "description": "Description of the image"
                        },
                        "gallery": {
                            "bsonType": ["string", "null"],
                            "description": "Gallery to which the image belongs"
                        }
                    }
                }
            },
            "validationLevel": "strict",
            "validationAction": "error"
        }

        # Get existing collections
        collections = db_c.db.list_collection_names()
        if IMG.COLLECTION_NAME in collections:
            # skip
            return
            

        db_c.db.create_collection(
            name=IMG.COLLECTION_NAME,
            validator=schema["validator"],
            validationLevel=schema["validationLevel"],
            validationAction=schema["validationAction"]
        )

    @staticmethod
    def db_drop_collection(db_c: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for images.
        """
        db_c.db.drop_collection(IMG.COLLECTION_NAME)
    
    @staticmethod
    def _image_to_bytes(img: Image.Image, format: str = "PNG") -> bytes:
        """
        Convert a PIL Image to bytes.
        """
        with BytesIO() as output:
            img.save(output, format=format)
            return output.getvalue()

    @staticmethod
    def _bytes_to_image(data: bytes) -> Image.Image:
        """
        Convert bytes data to a PIL Image.
        """
        return Image.open(BytesIO(data))
    
    @staticmethod
    def _db_load(data: dict) -> 'IMG':
        """
        Load an IMG object from a dictionary (as retrieved from MongoDB).
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

        image = IMG._bytes_to_image(img_data)
        
        return IMG(
            img=image,
            name=data.get("name", ""),
            description=data.get("description", ""),
            gallery=data.get("gallery"),
            _id=str(data.get("_id"))
        )

    
    def db_save(self, db_c: MongoDBConnection) -> None:
        """
        Save the IMG object to MongoDB.
        Converts the PIL Image to binary data before insertion.
        """
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        data = self.to_dict()
        data["img"] = IMG._image_to_bytes(self.img)
        collection.insert_one(data)
    
    @staticmethod
    def db_find(db_c: MongoDBConnection, _id: str) -> Optional['IMG']:
        """
        Find the IMG object in the database by _id.
        Returns an IMG instance if found, else None.
        """
        collection: Collection = db_c.db[IMG.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return IMG._db_load(data)
        return None
    
    def db_update(self, db_c: MongoDBConnection) -> None:
        """
        Update the IMG object in the database.
        """
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        data = self.to_dict()
        data["img"] = IMG._image_to_bytes(self.img)
        collection.update_one({"_id": self._id}, {"$set": data})
    
    def db_delete(self, db_c: MongoDBConnection) -> None:
        """
        Delete the IMG object from the database.
        """
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})
    
    @staticmethod
    def db_find_all(db_c: MongoDBConnection) -> List['IMG']:
        """
        Find all IMG objects in the database.
        Returns a list of IMG instances.
        """
        collection: Collection = db_c.db[IMG.COLLECTION_NAME]
        docs = collection.find()
        return [IMG._db_load(doc) for doc in docs]
    
    @staticmethod
    def db_delete_by_gallery(db_c: MongoDBConnection, gallery_id: str) -> None:
        """
        Delete all IMG objects belonging to a specific gallery from the database.
        """
        collection: Collection = db_c.db[IMG.COLLECTION_NAME]
        collection.delete_many({"gallery": gallery_id})
