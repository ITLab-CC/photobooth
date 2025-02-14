from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
from PIL import Image
import uuid
import json


@dataclass
class Gallery:
    creation_time: datetime
    expiration_time: datetime
    _id: str = field(default_factory=lambda: f"IMG-{uuid.uuid4()}")

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        """Convert the object to a dictionary."""
        return {
            "id": self._id,  # Note: MongoDB uses _id as the primary key.
            "creation_time": self.creation_time,
            "expiration_time": self.expiration_time
        }

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
        return json.dumps({
            "id": self._id,
            "creation_time": self.creation_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expiration_time": self.expiration_time.strftime("%Y-%m-%d %H:%M:%S")
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
    def _mongodb_collection() -> dict:
        """
        Returns the options to create a collection in MongoDB with validation.
        """
        return {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "creation_time", "expiration_time"],
                    "properties": {
                        "_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the image, required and acts as primary key"
                        },
                        "creation_time": {
                            "bsonType": "date",
                            "description": "The time the gallery was created"
                        },
                        "expiration_time": {
                            "bsonType": "date",
                            "description": "The time the gallery will be deleted"
                        }
                    }
                }
            },
            "validationLevel": "strict",
            "validationAction": "error"
        }

