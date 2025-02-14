from dataclasses import dataclass, field, asdict
from typing import Optional
from PIL import Image
import uuid
import json


@dataclass
class IMG:
    img: Image.Image
    name: str
    description: str
    gallery: Optional[str] = None
    _id: str = field(default_factory=lambda: f"IMG-{uuid.uuid4()}")

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """Convert the object to a dictionary."""
        return {
            "_id": self._id,  # Note: MongoDB uses _id as the primary key.
            "name": self.name,
            "description": self.description,
            "img": self.img,
            "gallery": self.gallery
        }

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
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
    def _mongodb_collection() -> dict:
        """
        Returns the options to create a collection in MongoDB with validation.
        """
        return {
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

