import asyncio

from db_connection import MongoDBConnection
from user import User
from img import IMG
from gallery import Gallery
from session import SessionManager

def main() -> None:
    # This will setup the db with all the users and roles.
    # It wil also create the users in the db

    MONGODB_URI = "localhost:27017"
    MONGODB_ADMIN_USER = "root"
    MONGODB_ADMIN_PASSWORD = "example"
    MONGODB_DB_NAME = "photo_booth"

    ADMIN_USER = "boss"
    ADMIN_PASSWORD = "admin"
    VIEWER_USER = "viewer"
    VIEWER_PASSWORD = "viewer"

    admin_db = MongoDBConnection(
        mongo_uri=MONGODB_URI,
        user=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        db_name=MONGODB_DB_NAME,
        admin=True
    )

    # Drop all collections (TODO: remove this in production)
    User.db_drop_collection(admin_db)
    Gallery.db_drop_collection(admin_db)
    IMG.db_drop_collection(admin_db)

    # Create all collections
    User.db_create_collection(admin_db)
    Gallery.db_create_collection(admin_db)
    IMG.db_create_collection(admin_db)

    # Create roles
    admin_db.create_roles([User, Gallery, IMG])

    # Create users
    admin_db.create_user(ADMIN_USER, ADMIN_PASSWORD, ["boss"])
    admin_db.create_user(VIEWER_USER, VIEWER_PASSWORD, ["user_viewer"])


    admin_password_hash, admin_password_salt = SessionManager.hash_password(ADMIN_PASSWORD)
    admin_user = User(
        username=ADMIN_USER,
        password_hash=admin_password_hash,
        password_salt=admin_password_salt,
        roles=["boss"]
    )
    admin_user.db_save(admin_db)

    viewer_password_hash, viewer_password_salt = SessionManager.hash_password(VIEWER_PASSWORD)
    viewer_user = User(
        username=VIEWER_USER,
        password_hash=viewer_password_hash,
        password_salt=viewer_password_salt,
        roles=["user_viewer"]
    )
    viewer_user.db_save(admin_db)

    # print user with roles
    users = admin_db.db.command("usersInfo")["users"]
    for user in users:
        if user["user"] in ["boss", "viewer"]:
            print(user["user"], user["roles"])

    admin_db.close()

    async def test() -> None:

        # get db VIEWER_USER
        db_viewer_user = MongoDBConnection(
            mongo_uri=MONGODB_URI,
            user=VIEWER_USER,
            password=VIEWER_PASSWORD,
            db_name=MONGODB_DB_NAME
        )

        # test login
        sm = SessionManager()
        session = await sm.login(db_viewer_user, ADMIN_USER, ADMIN_PASSWORD, None)
        print(f"Created session: {session._id}, Status: {session.status}")
        print(f"Session user: {session.user.username}")

    asyncio.run(test())

if __name__ == "__main__":
    main()