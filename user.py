import inspect
import uuid
import enum
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Union, Callable

import bcrypt
from db_connection import MongoDBConnection

# Use Python's enum module instead of the built-in enumerate.
class UserRoles(enum.Enum):
    PHOTO_BOOTH = "photo_booth"
    EXPIRATION_DELETER = "expiration_deleter"
    USER_VIEWER = "user_viewer"
    PRINTER = "printer"
    BOSS = "boss"

import enum

class MongoDBPermissions(enum.Enum):
    # Read and Write Actions
    FIND = "find"
    INSERT = "insert"
    REMOVE = "remove"
    UPDATE = "update"
    BYPASS_DOCUMENT_VALIDATION = "bypassDocumentValidation"

    # User and Role Management Actions
    CREATE_ROLE = "createRole"
    CREATE_USER = "createUser"
    DROP_ROLE = "dropRole"
    DROP_USER = "dropUser"
    GRANT_ROLE = "grantRole"
    REVOKE_ROLE = "revokeRole"
    VIEW_ROLE = "viewRole"
    VIEW_USER = "viewUser"

    # Database Management Actions
    CHANGE_STREAM = "changeStream"
    CHANGE_STREAM_INVALIDATE = "changeStreamInvalidate"
    COLL_MOD = "collMod"
    COMPACT = "compact"
    CONVERT_TO_CAPPED = "convertToCapped"
    CREATE_COLLECTION = "createCollection"
    CREATE_INDEX = "createIndex"
    DROP_COLLECTION = "dropCollection"
    DROP_INDEX = "dropIndex"
    EMPTY_CAPPED = "emptycapped"
    LIST_COLLECTIONS = "listCollections"
    LIST_INDEXES = "listIndexes"
    RENAME_COLLECTION_SAME_DB = "renameCollectionSameDB"

    # Replication and Sharding Actions
    ADD_SHARD = "addShard"
    REPL_SET_CONFIGURE = "replSetConfigure"
    REPL_SET_GET_STATUS = "replSetGetStatus"
    RESYNC = "resync"
    SHUTDOWN = "shutdown"
    SPLIT_VECTOR = "splitVector"
    SPLIT_CHUNK = "splitChunk"
    MOVE_CHUNK = "moveChunk"

    # Server Administration Actions
    ENABLE_SHARDING = "enableSharding"
    FLUSH_ROUTER_CONFIG = "flushRouterConfig"
    INVALIDATE_USER_CACHE = "invalidateUserCache"
    KILL_CURSORS = "killCursors"
    KILL_ANY_CURSOR = "killAnyCursor"
    KILLOP = "killop"
    LOG_ROTATE = "logRotate"
    NETSTAT = "netstat"
    SERVER_STATUS = "serverStatus"
    TOP = "top"

    # Backup and Restore Actions
    BACKUP = "backup"
    RESTORE = "restore"

    # Profiling and Monitoring Actions
    PROFILE = "profile"
    VALIDATE = "validate"
    VIEW_AUDIT_LOG = "viewAuditLog"
    VIEW_PROFILER = "viewProfiler"

    # Special Administrative Actions
    ANY_ACTION = "anyAction"
    SET_PARAMETER = "setParameter"

def mongodb_permissions(collection: str, actions: List[MongoDBPermissions], roles: List[UserRoles]) -> Callable:
    """A decorator to attach metadata to methods."""
    def decorator(func):
        func.__annotations__ = {"mongodb_permissions": {"collection": collection, "actions": actions, "roles": roles}}
        return func
    return decorator

def mongodb_get_user_permissions(
    cls, 
    db_name: str, 
    roles: List[UserRoles]
) -> List[Dict[str, Union[Dict[str, str], List[str]]]]:
    annotated_methods = {}

    for name, method in inspect.getmembers(cls):
        # Unwrap if the member is a bound method (including class methods)
        func = getattr(method, "__func__", None)
        if func is None:
            if inspect.isfunction(method):
                func = method
            else:
                continue

        annotations = getattr(method, "__annotations__", {})
        if "mongodb_permissions" in annotations:
            if not any(role in roles for role in annotations["mongodb_permissions"]["roles"]):
                continue

            annotated_methods[name] = annotations["mongodb_permissions"]

    # for each method, get the metadata and combine the actions of the same collection
    # goal to create a list like this:
    # [
    #     {"resource": {"db": MONGODB_DB_NAME, "collection": Gallery.COLLECTION_NAME}, "actions": ["insert"]},
    #     {"resource": {"db": MONGODB_DB_NAME, "collection": IMG.COLLECTION_NAME}, "actions": ["insert", "find"]}
    # ]
    permissions: List[Dict[str, Union[Dict[str, str], List[str]]]] = []
    for method, metadata in annotated_methods.items():
        collection = str(metadata["collection"])
        if collection not in [p["resource"]["collection"] for p in permissions]:
            permissions.append({
                "resource": {"db": db_name, "collection": collection},
                "actions": [ac.value for ac in metadata["actions"]]
            })
        else:
            for p in permissions:
                if p["resource"]["collection"] == collection:
                    for ac in metadata["actions"]:
                        if ac.value not in p["actions"]:
                            p["actions"].append(ac.value)
    
    return permissions


# Define a module-level constant for the collection name.
USERS_COLLECTION = "users"

@dataclass
class User:
    username: str
    password_hash: str
    password_salt: str
    last_login: datetime
    roles: List[UserRoles] = field(default_factory=list)
    _id: str = field(default_factory=lambda: f"USER-{uuid.uuid4()}")

    # Collection name for MongoDB.
    COLLECTION_NAME: str = USERS_COLLECTION

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
            "roles": [role.value for role in self.roles]
        }

    def __str__(self) -> str:
        """Return a JSON representation of the object."""
        return json.dumps({
            "id": self._id,
            "username": self.username,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S"),
            "roles": [role.value for role in self.roles]
        }, indent=4)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, User):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.CREATE_COLLECTION], roles=[UserRoles.BOSS])
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
                        "roles": {
                            "bsonType": "array",
                            "description": "must be an array and is required",
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
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.DROP_COLLECTION], roles=[UserRoles.BOSS])
    def db_drop_collection(cls, db_connection: MongoDBConnection) -> None:
        """
        Drop the MongoDB collection for users.
        """
        db_connection.db.drop_collection(cls.COLLECTION_NAME)

    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.INSERT], roles=[UserRoles.BOSS])
    def db_save(self, db_connection: MongoDBConnection) -> None:
        """
        Save the user object to MongoDB.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.insert_one(data)

    @classmethod
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.FIND], roles=[UserRoles.BOSS, UserRoles.USER_VIEWER])
    def db_find(cls, db_connection: MongoDBConnection, _id: str) -> Optional['User']:
        """
        Find a User object in the database by _id.
        Returns a User instance if found, else None.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        data = collection.find_one({"_id": _id})
        if data:
            return cls._db_load(data)
        return None

    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.UPDATE], roles=[UserRoles.BOSS])
    def db_update(self, db_connection: MongoDBConnection) -> None:
        """
        Update the User object in the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        data = self.to_dict()
        collection.update_one({"_id": self._id}, {"$set": data})

    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.REMOVE], roles=[UserRoles.BOSS])
    def db_delete(self, db_connection: MongoDBConnection) -> None:
        """
        Delete the User object from the database.
        """
        collection = db_connection.db[self.COLLECTION_NAME]
        collection.delete_one({"_id": self._id})

    @classmethod
    @mongodb_permissions(collection=USERS_COLLECTION, actions=[MongoDBPermissions.FIND], roles=[UserRoles.BOSS, UserRoles.USER_VIEWER])
    def db_find_all(cls, db_connection: MongoDBConnection) -> List['User']:
        """
        Retrieve all User objects from the database.
        """
        collection = db_connection.db[cls.COLLECTION_NAME]
        docs = collection.find()
        return [cls._db_load(doc) for doc in docs]

    @classmethod
    def _db_load(cls, data: dict) -> 'User':
        """Convert a MongoDB document into a User instance."""
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            password_salt=data["password_salt"],
            last_login=data["last_login"],
            roles=[UserRoles(role) for role in data.get("roles", [])],
            _id=data["_id"]
        )

def role_exists(admin_db, role_name: str) -> bool:
    """Check if a role already exists in MongoDB."""
    roles_info = admin_db.db.command("rolesInfo", role_name)
    roles_list = roles_info.get("roles", [])
    return any(role.get("role") == role_name for role in roles_list)

def remove_role(admin_db, role_name: str) -> None:
    """Remove an existing role if it exists."""
    if role_exists(admin_db, role_name):
        admin_db.db.command("dropRole", role_name)

def main() -> None:
    MONGODB_URI = "localhost:27017"
    MONGODB_ADMIN_USER = "root"
    MONGODB_ADMIN_PASSWORD = "example"
    MONGODB_DB_NAME = "photo_booth"

    admin_db = MongoDBConnection(
        mongo_uri=MONGODB_URI,
        user=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        db_name=MONGODB_DB_NAME
    )

    User.db_drop_collection(admin_db)
    User.db_create_collection(admin_db)

    roles = mongodb_get_user_permissions(User, MONGODB_DB_NAME, [UserRoles.BOSS])
    print(roles)
    # When removing/creating roles via db commands, use the enum's value.
    remove_role(admin_db, UserRoles.BOSS.value)
    admin_db.db.command("createRole", UserRoles.BOSS.value, privileges=roles, roles=[])
    print("Role created")

if __name__ == "__main__":
    main()
