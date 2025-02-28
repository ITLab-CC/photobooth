from db_connection import MongoDBConnection
from gallery import Gallery
from img import IMG

MONGODB_URI = "localhost:27017"
MONGODB_ADMIN_USER = "root"
MONGODB_ADMIN_PASSWORD = "example"
MONGODB_DB_NAME = "photo_booth"

def role_exists(admin_db, role_name):
    """Check if a role already exists in MongoDB."""
    roles = admin_db.db.command("rolesInfo", role_name).get("roles", [])
    return any(role.get("role") == role_name for role in roles)

def remove_role(admin_db, role_name):
    """Remove an existing role if it exists."""
    if role_exists(admin_db, role_name):
        admin_db.db.command("dropRole", role_name)

def main():
    admin_db = MongoDBConnection(
        mongo_uri=MONGODB_URI,
        user=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        db_name=MONGODB_DB_NAME
    )

    # Drop all collections (TODO: remove this in production)
    Gallery.db_drop_collection(admin_db)
    IMG.db_drop_collection(admin_db)

    # Create all collections
    Gallery.db_create_collection(admin_db)
    IMG.db_create_collection(admin_db)

    # Create roles
    # photo_booth:
    #  - create galleries
    #  - create images
    #  - view images
    #  - view galleries

    # user_viewer:
    #  - view images
    #  - view galleries

    # expiration_deleter:
    #  - delete expired galleries

    # boss:
    #  - admin all
    roles = {
        "photo_booth": [
            {"resource": {"db": MONGODB_DB_NAME, "collection": Gallery.COLLECTION_NAME}, "actions": ["insert"]},
            {"resource": {"db": MONGODB_DB_NAME, "collection": IMG.COLLECTION_NAME}, "actions": ["insert", "find"]}
        ],
        "user_viewer": [
            {"resource": {"db": MONGODB_DB_NAME, "collection": Gallery.COLLECTION_NAME}, "actions": ["find"]},
            {"resource": {"db": MONGODB_DB_NAME, "collection": IMG.COLLECTION_NAME}, "actions": ["find"]}
        ],
        "expiration_deleter": [
            {"resource": {"db": MONGODB_DB_NAME, "collection": Gallery.COLLECTION_NAME}, "actions": ["remove"]},
            {"resource": {"db": MONGODB_DB_NAME, "collection": IMG.COLLECTION_NAME}, "actions": ["remove"]}
        ],
        "boss": [
            {"resource": {"db": MONGODB_DB_NAME, "collection": Gallery.COLLECTION_NAME}, "actions": ["insert", "find", "dropCollection"]},
            {"resource": {"db": MONGODB_DB_NAME, "collection": IMG.COLLECTION_NAME}, "actions": ["insert", "find", "dropCollection"]}
        ]
    }

    # Remove and recreate roles
    for role_name, privileges in roles.items():
        remove_role(admin_db, role_name)  # Remove existing role
        admin_db.db.command("createRole", role_name, privileges=privileges, roles=[])

    # Create users
    # photo_booth_user
    # user_viewer_user
    # expiration_deleter_user
    # boss_user
    users = {
        "photo_booth_user": ("photo_booth_password", ["photo_booth"]),
        "user_viewer_user": ("user_viewer_password", ["user_viewer"]),
        "expiration_deleter_user": ("expiration_deleter_password", ["expiration_deleter"]),
        "boss_user": ("boss_password", ["boss"])
    }

    for user, (password, roles) in users.items():
        admin_db.db.command("createUser", user, pwd=password, roles=roles)

    # Close the admin connection
    admin_db.close()

if __name__ == "__main__":
    main()
