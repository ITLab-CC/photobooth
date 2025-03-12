import uuid
from typing import Optional, List
from dataclasses import dataclass, field
from pymongo.collection import Collection
from db_connection import MongoDBConnection, mongodb_permissions, MongoDBPermissions
from datetime import datetime

PRINTER_QUEUE_COLLECTION = "printer_queue"

@dataclass
class PrinterQueueItem:
    img_id: str
    number: int
    created_at: datetime = field(default_factory=datetime.now)
    _id: str = field(default_factory=lambda: f"Print-{uuid.uuid4()}")

    COLLECTION_NAME: str = PRINTER_QUEUE_COLLECTION

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "img_id": self.img_id,
            "number": self.number,
            "created_at": self.created_at,
        }

    @classmethod
    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.CREATE_COLLECTION], roles=["boss"])
    def db_create_collection(cls, db_c: MongoDBConnection) -> None:
        schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "img_id", "number", "created_at"],
                    "properties": {
                        "_id": {"bsonType": "string"},
                        "img_id": {"bsonType": "string"},
                        "number": {"bsonType": "int"},
                        "created_at": {"bsonType": "date"}
                    }
                }
            },
            "validationLevel": "strict",
            "validationAction": "error"
        }
        if cls.COLLECTION_NAME not in db_c.db.list_collection_names():
            db_c.db.create_collection(
                name=cls.COLLECTION_NAME,
                validator=schema["validator"],
                validationLevel=schema["validationLevel"],
                validationAction=schema["validationAction"]
            )

    @classmethod
    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.DROP_COLLECTION], roles=["boss"])
    def db_drop_collection(cls, db_c: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for images.
        """
        db_c.db.drop_collection(cls.COLLECTION_NAME)

    @classmethod
    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "printer", "photo_booth"])
    def get_next_number(self, db_c: MongoDBConnection) -> int:
        collection: Collection = db_c.db[PRINTER_QUEUE_COLLECTION]
        last_item = collection.find_one(sort=[("number", -1)])
        if last_item is None:
            return 1
        return last_item["number"] + 1

    @classmethod
    def _db_load(cls, data: dict) -> 'PrinterQueueItem':
        return cls(
            img_id=data["img_id"],
            created_at=data["created_at"],
            number=data["number"],
            _id=data["_id"]
        )

    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.INSERT], roles=["boss", "photo_booth"])
    def db_save(self, db_c: MongoDBConnection) -> None:
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        collection.insert_one(self.__dict__)

    @classmethod
    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "printer"])
    def db_find(cls, db_c: MongoDBConnection, _id: str) -> Optional['PrinterQueueItem']:
        collection: Collection = db_c.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data is None:
            return None
        return cls._db_load(data)

    @classmethod
    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.FIND], roles=["boss", "printer"])
    def db_find_all(cls, db_c: MongoDBConnection) -> List['PrinterQueueItem']:
        collection: Collection = db_c.db[cls.COLLECTION_NAME]
        return [cls._db_load(data) for data in collection.find()]
    
    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.REMOVE], roles=["boss", "printer"])
    def db_delete(self, db_c: MongoDBConnection) -> None:
        collection: Collection = db_c.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})

    @classmethod
    @mongodb_permissions(collection=PRINTER_QUEUE_COLLECTION, actions=[MongoDBPermissions.REMOVE], roles=["boss"])
    def clear_queue(cls, db_c: MongoDBConnection) -> None:
        collection: Collection = db_c.db[cls.COLLECTION_NAME]
        collection.delete_many({})