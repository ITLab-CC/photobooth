import inspect
import enum
from typing import Dict, Optional, List, Set, Tuple, Union, Callable

from pymongo import MongoClient
from pymongo.database import Database

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

def mongodb_permissions(collection: str, actions: List[MongoDBPermissions], roles: List[str]) -> Callable:
    """A decorator to attach metadata to methods."""
    def decorator(func):
        func.__annotations__ = {"mongodb_permissions": {"collection": collection, "actions": actions, "roles": roles}}
        return func
    return decorator

def mongodb_get_user_permissions(
    classes: Union[type, List[type]],
    db_name: str, 
    roles: Union[str, List[str]]
) -> List[Dict[str, Union[Dict[str, str], List[str]]]]:
    # Use a dict to aggregate permissions per collection
    permissions_by_collection: Dict[str, Set[str]] = {}

    # if classes is only a single class, convert it to a list
    if not isinstance(classes, list):
        classes = [classes]
    if not isinstance(roles, list):
        roles = [roles]

    # Iterate over each class in the list
    for cls in classes:
        for name, method in inspect.getmembers(cls):
            # Unwrap bound methods (e.g. classmethods)
            func = getattr(method, "__func__", None)
            if func is None:
                if inspect.isfunction(method):
                    func = method
                else:
                    continue

            annotations = getattr(func, "__annotations__", {})
            if "mongodb_permissions" in annotations:
                metadata = annotations["mongodb_permissions"]
                # Skip if none of the roles match
                if not any(role in roles for role in metadata["roles"]):
                    continue

                collection = str(metadata["collection"])
                actions = {ac.value for ac in metadata["actions"]}

                if collection in permissions_by_collection:
                    permissions_by_collection[collection].update(actions)
                else:
                    permissions_by_collection[collection] = actions

    # Build the permissions list with explicit type annotations
    permissions: List[Dict[str, Union[Dict[str, str], List[str]]]] = []
    for collection, actions in permissions_by_collection.items():
        perm: Dict[str, Union[Dict[str, str], List[str]]] = {
            "resource": {"db": db_name, "collection": collection},
            "actions": list(actions)
        }
        permissions.append(perm)
    
    return permissions

def mongodb_get_roles(classes: Union[type, List[type]]) -> List[str]:
    # if classes is only a single class, convert it to a list
    if not isinstance(classes, list):
        classes = [classes]

    roles = set()
    for cls in classes:
        for name, method in inspect.getmembers(cls):
            # Unwrap bound methods (e.g. classmethods)
            func = getattr(method, "__func__", None)
            if func is None:
                if inspect.isfunction(method):
                    func = method
                else:
                    continue

            annotations = getattr(func, "__annotations__", {})
            if "mongodb_permissions" in annotations:
                metadata = annotations["mongodb_permissions"]
                roles.update(metadata["roles"])

    return list(roles)


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

    def get_roles(self, role_name: str) -> List[str]:
        """Check if a role already exists in MongoDB."""
        roles_info = self.db.command("rolesInfo", role_name)
        roles_list = roles_info.get("roles", [])
        return [role.get("role") for role in roles_list]

    def remove_role(self, role_name: str) -> None:
        """Remove an existing role if it exists."""
        if role_name in self.get_roles(role_name):
            self.db.command("dropRole", role_name)

    def create_roles(self, classes: Union[type, List[type]]) -> List[str]:
        """
        Create roles in the MongoDB database based on the annotations of the methods in the classes.
        """
        # get a list of all roles
        roles = mongodb_get_roles(classes)

        for role in roles:
            permissions = mongodb_get_user_permissions(classes, self.db_name, role)
            # remove existing role
            self.remove_role(role)
            # create new role
            self.db.command("createRole", role, privileges=permissions, roles=[])

        return roles
        
    def get_users(self) -> List[str]:
        """
        Get all users in the MongoDB database.
        """
        return [user["user"] for user in self.db.command("usersInfo").get("users", [])]
    
    def remove_user(self, user: str) -> None:
        """
        Remove a user from the MongoDB database.
        """
        if user in self.get_users():
            self.db.command("dropUser", user)

    def create_user(self, name, password, roles):
        """
        Create users in the MongoDB database.
        """
        if name in self.get_users():
            self.remove_user(name)
        
        self.db.command("createUser", name, pwd=password, roles=roles)


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

    from user import User
    admin_db.create_roles(User)

    # print role
    print(admin_db.db.command("rolesInfo", "boss", showPrivileges=True))
    print(admin_db.db.command("rolesInfo", "user_viewer", showPrivileges=True))

    # create user
    admin_db.create_user("admin", "admin", ["boss"])
    admin_db.create_user("viewer", "viewer", ["user_viewer"])

    # print user with roles
    users = admin_db.db.command("usersInfo")["users"]
    for user in users:
        if user["user"] in ["admin", "viewer"]:
            print(user["user"], user["roles"])

    admin_db.close()

if __name__ == "__main__":
    main()