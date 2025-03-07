import asyncio

from db_connection import MongoDBConnection
from user import User
from img import IMG
from background import Background
from gallery import Gallery
from session import SessionManager

def setup() -> None:
    # This will setup the db with all the users and roles.
    # It wil also create the users in the db

    MONGODB_URI = "localhost:27017"
    MONGODB_ADMIN_USER = "root"
    MONGODB_ADMIN_PASSWORD = "example"
    MONGODB_DB_NAME = "photo_booth"

    # Is god, the son of root
    ADMIN = "boss"
    ADMIN_PASSWORD = "admin"
    
    # can read the users
    LOGIN_MANAGER = "login_manager"
    LOGIN_MANAGER_PASSWORD = "login_manager"

    # can create images and galleries
    PHOTO_BOOTH = "photo_booth"
    PHOTO_BOOTH_PASSWORD = "photo_booth"

    # can view, delete images and galleries
    IMG_VIEWER = "img_viewer"
    IMG_VIEWER_PASSWORD = "img_viewer"

    # can view, delete images and galleries
    OLD_IMG_ERASER = "old_img_eraser"
    OLD_IMG_ERASER_PASSWORD = "old_img_eraser"


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
    Background.db_drop_collection(admin_db)

    # Create all collections
    User.db_create_collection(admin_db)
    Gallery.db_create_collection(admin_db)
    IMG.db_create_collection(admin_db)
    Background.db_create_collection(admin_db)

    # Create roles based on the annotations
    admin_db.create_roles([User, Gallery, IMG, Background])

    # Create users
    admin_db.create_user(ADMIN, ADMIN_PASSWORD, ["boss"])
    admin_db.create_user(LOGIN_MANAGER, LOGIN_MANAGER_PASSWORD, ["login_manager"])
    admin_db.create_user(PHOTO_BOOTH, PHOTO_BOOTH_PASSWORD, ["photo_booth"])
    admin_db.create_user(IMG_VIEWER, IMG_VIEWER_PASSWORD, ["img_viewer"])
    admin_db.create_user(OLD_IMG_ERASER, OLD_IMG_ERASER_PASSWORD, ["old_img_eraser"])


    admin_password_hash, admin_password_salt = SessionManager.hash_password(ADMIN_PASSWORD)
    admin_user = User(
        username=ADMIN,
        password_hash=admin_password_hash,
        password_salt=admin_password_salt,
        roles=["boss"]
    )
    admin_user.db_save(admin_db)

    # # print user with roles
    # users = admin_db.db.command("usersInfo")["users"]
    # for user in users:
    #     if user["user"] in ["boss", "viewer"]:
    #         print(user["user"], user["roles"])

    # async def test() -> None:

    #     # get db VIEWER_USER
    #     db_viewer_user = MongoDBConnection(
    #         mongo_uri=MONGODB_URI,
    #         user=VIEWER_USER,
    #         password=VIEWER_PASSWORD,
    #         db_name=MONGODB_DB_NAME
    #     )

    #     # test login
    #     sm = SessionManager()
    #     session = await sm.login(db_viewer_user, ADMIN_USER, ADMIN_PASSWORD, None)
    #     print(f"Created session: {session._id}, Status: {session.status}")
    #     print(f"Session user: {session.user.username}")

    #     user = User.db_find_all(db_viewer_user)
    #     print(f"User count: {len(user)}")
    #     for u in user:
    #         print(u.username)

    #     # test create user with viewer
    #     new_user = User(
    #         username="new_user",
    #         password_hash="password_hash",
    #         password_salt="password_salt",
    #         roles=["login_manager"]
    #     )
    #     try:
    #         new_user.db_save(db_viewer_user)
    #     except Exception as e:
    #         print(e)

    #     # test logout
    #     await session.logout()

    # asyncio.run(test())

    admin_db.close()

if __name__ == "__main__":
    setup()