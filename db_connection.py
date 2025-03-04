import inspect
import enum
from typing import Dict, Optional, List, Union, Callable

from pymongo import MongoClient
from pymongo.database import Database

class MongoDBConnection:
    def __init__(self,
                 mongo_uri: str,
                 user: str,
                 password: str,
                 db_name: str,
                ) -> None:
        self.mongo_uri = mongo_uri
        self.user = user
        self.password = password
        self.db_name = db_name

        new_uri = f"mongodb://{user}:{password}@{mongo_uri}"
        self.client: MongoClient = MongoClient(new_uri)
        self.db: Database = self.client[db_name]

    def close(self) -> None:
        """
        Close the MongoDB client.
        """
        self.client.close()




# Use Python's enum module instead of the built-in enumerate.
class UserRoles(enum.Enum):
    PHOTO_BOOTH = "photo_booth"
    EXPIRATION_DELETER = "expiration_deleter"
    USER_VIEWER = "user_viewer"
    PRINTER = "printer"
    BOSS = "boss"

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