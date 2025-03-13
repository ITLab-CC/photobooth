import argparse
import os
import secrets
import string
from typing import Optional

from dotenv import load_dotenv, dotenv_values
from db_connection import MongoDBConnection
import printer
from user import User
from img import IMG
from background import Background
from gallery import Gallery
from session import SessionManager
from printer import PrinterQueueItem


def generate_password(length=32):
    chars = string.ascii_letters + string.digits + "!#%&*+,-./:;<=>?@^_|~"
    return ''.join(secrets.choice(chars) for _ in range(length))


def connect_db(db_url, db_root, db_pw, db_name):
    return MongoDBConnection(
        mongo_uri=db_url,
        user=db_root,
        password=db_pw,
        db_name=db_name,
        admin=True
    )


def create_user_account(admin_db: MongoDBConnection, username: str, password: Optional[str], roles: list[str], show_pw=False) -> None:
    password_new: str = ""
    if not password:
        password_new = generate_password()
    else:
        password_new = password

    # check if the user already exists
    if User.db_find_by_username(admin_db, username):
        print(f"ERROR: User {username} already exists.")
        exit(1)

    admin_db.create_user(username, password_new, roles)
    password_hash, password_salt = SessionManager.hash_password(password_new)
    user = User(
        username=username,
        password_hash=password_hash,
        password_salt=password_salt,
        roles=roles
    )
    user.db_save(admin_db)

    # Print out the admin (boss) account details for the user
    print("---------------Account---------------")
    print(f"Username: {username}")
    print(f"Roles: {roles}")
    if password is None or show_pw:
        print(f"Password: {password_new}")
    else:
        print(f"Password: ********")
    print("--------------------------------------")


def setup(db_url, db_root, db_pw, db_name) -> None:
    # Get account settings from environment (or use defaults if missing)
    LOGIN_MANAGER = os.getenv("LOGIN_MANAGER", "login_manager")
    LOGIN_MANAGER_PASSWORD = os.getenv("LOGIN_MANAGER_PASSWORD", generate_password())
    IMG_VIEWER = os.getenv("IMG_VIEWER", "img_viewer")
    IMG_VIEWER_PASSWORD = os.getenv("IMG_VIEWER_PASSWORD", generate_password())
    OLD_IMG_ERASER = os.getenv("OLD_IMG_ERASER", "old_img_eraser")
    OLD_IMG_ERASER_PASSWORD = os.getenv("OLD_IMG_ERASER_PASSWORD", generate_password())

    # Connect to the database
    admin_db = connect_db(db_url, db_root, db_pw, db_name)

    # Clean up existing collections
    User.db_drop_collection(admin_db)
    Gallery.db_drop_collection(admin_db)
    IMG.db_drop_collection(admin_db)
    Background.db_drop_collection(admin_db)
    PrinterQueueItem.db_drop_collection(admin_db)

    # Create collections
    User.db_create_collection(admin_db)
    Gallery.db_create_collection(admin_db)
    IMG.db_create_collection(admin_db)
    Background.db_create_collection(admin_db)
    PrinterQueueItem.db_create_collection(admin_db)

    # Create roles based on the given models
    admin_db.create_roles([User, Gallery, IMG, Background, PrinterQueueItem])

    # Create additional users (using the DB layer’s user creation, without ORM password hashing)
    admin_db.create_user(LOGIN_MANAGER, LOGIN_MANAGER_PASSWORD, ["login_manager"])
    admin_db.create_user(IMG_VIEWER, IMG_VIEWER_PASSWORD, ["img_viewer"])
    admin_db.create_user(OLD_IMG_ERASER, OLD_IMG_ERASER_PASSWORD, ["old_img_eraser"])

    admin_db.close()


def create_admin(db_url, db_root, db_pw, db_name, username=None, password=None, generate_pw=False) -> None:
    # Connect to the database
    admin_db = connect_db(db_url, db_root, db_pw, db_name)

    if not username:
        username = input("Enter the username for the admin account (default: boss): ") or "boss"
    if not password and not generate_pw:
        password = input("Enter the password for the admin account (default: random): ") or None

    # Create the various user accounts
    create_user_account(admin_db, username, password, ["boss"])


def create_photo_booth(db_url, db_root, db_pw, db_name, username="photo_booth", password=None, generate_pw=False) -> None:
    # Connect to the database
    admin_db = connect_db(db_url, db_root, db_pw, db_name)

    if not username:
        username = input("Enter the username for the photo_booth account (default: photo_booth): ") or "photo_booth"
    if not password and not generate_pw:
        password = input("Enter the password for the photo_booth account (default: random): ") or None

    # Create the various user accounts
    create_user_account(admin_db, username, password, ["photo_booth"])


def create_printer(db_url, db_root, db_pw, db_name, username="printer", password=None, generate_pw=False, show_pw=False) -> None:
    # Connect to the database
    admin_db = connect_db(db_url, db_root, db_pw, db_name)

    if not username:
        username = input("Enter the username for the printer account (default: printer): ") or "printer"
    if not password and not generate_pw:
        password = input("Enter the password for the printer account (default: random): ") or None

    # Create the various user accounts
    create_user_account(admin_db, username, password, ["printer"], show_pw=show_pw)


def create_default_env():
    """
    Creates a default .env file with the necessary configuration values
    and also creates a default .env for the print service.
    """
    # Generate random passwords for the non-admin service accounts
    login_manager_password = generate_password()
    img_viewer_password = generate_password()
    old_img_eraser_password = generate_password()

    db_admin_password = generate_password()

    with open('.env-dev', 'w') as env_file:
        env_file.write('BASE_URL="http://localhost:8000"\n')
        env_file.write('REDIS_URL="redis://localhost:6379"\n')
        env_file.write('MONGODB_URL="localhost:27017"\n')
        env_file.write('MONGODB_ADMIN_USER="root"\n')
        env_file.write(f'MONGODB_ADMIN_PASSWORD="{db_admin_password}"\n')
        env_file.write('MONGODB_DB_NAME="photo_booth"\n')
        env_file.write('LOGIN_MANAGER="login_manager"\n')
        env_file.write(f'LOGIN_MANAGER_PASSWORD="{login_manager_password}"\n')
        env_file.write('IMG_VIEWER="img_viewer"\n')
        env_file.write(f'IMG_VIEWER_PASSWORD="{img_viewer_password}"\n')
        env_file.write('OLD_IMG_ERASER="old_img_eraser"\n')
        env_file.write(f'OLD_IMG_ERASER_PASSWORD="{old_img_eraser_password}"\n')
        env_file.write(f'GALLERY_EXPIRATION_SECONDS="{60 * 60 * 24 * 7}"\n')  # 1 week
    
    with  open('.env', 'w') as env_file:
        env_file.write('BASE_URL="http://localhost:8000"\n')
        env_file.write('REDIS_URL="redis://redis:6379"\n')
        env_file.write('MONGODB_URL="mongodb:27017"\n')
        env_file.write('MONGODB_ADMIN_USER="root"\n')
        env_file.write(f'MONGODB_ADMIN_PASSWORD="{db_admin_password}"\n')
        env_file.write('MONGODB_DB_NAME="photo_booth"\n')
        env_file.write('LOGIN_MANAGER="login_manager"\n')
        env_file.write(f'LOGIN_MANAGER_PASSWORD="{login_manager_password}"\n')
        env_file.write('IMG_VIEWER="img_viewer"\n')
        env_file.write(f'IMG_VIEWER_PASSWORD="{img_viewer_password}"\n')
        env_file.write('OLD_IMG_ERASER="old_img_eraser"\n')
        env_file.write(f'OLD_IMG_ERASER_PASSWORD="{old_img_eraser_password}"\n')
        env_file.write(f'GALLERY_EXPIRATION_SECONDS="{60 * 60 * 24 * 7}"\n')  # 1 week

def check_dotenv(setup=False):
    if setup:
        required_keys = ["BASE_URL", "REDIS_URL", "MONGODB_URL", "MONGODB_ADMIN_USER", "MONGODB_ADMIN_PASSWORD",
                        "MONGODB_DB_NAME"]
    else:
        required_keys = ["BASE_URL", "REDIS_URL", "MONGODB_URL", "MONGODB_DB_NAME", "GALLERY_EXPIRATION_SECONDS"]
    error: bool = False
    for key in required_keys:
        if key not in os.environ:
            error = True
            print(f"Missing required key in .env file: {key}")
    if error:
        print("Please add the missing keys to the .env file or delete the file and run the script again.")
        exit(1)

def post_create_default_env(base_url: str, user: str = "printer", password: Optional[str] = None):
    # Create default print-service .env file
    if not os.path.exists("print-service"):
        os.makedirs("print-service")
    if not password:
        printer_password = generate_password()
    else:
        printer_password = password
    with open(os.path.join("print-service", ".env"), 'w') as env_file:
        env_file.write(f'PHOTO_BOOTH_BASE_URL="{base_url}"\n')
        env_file.write(f'PHOTO_BOOTH="{user}"\n')
        env_file.write(f'PHOTO_BOOTH_PASSWORD="{printer_password}"\n')

def main():
    # Argument parser
    parser = argparse.ArgumentParser(description="Setup script for MongoDB users and roles.")

    # Optional argument for skipping .env creation
    parser.add_argument("--skip-env", action="store_true", help="Skip the .env file creation.")

    # Mutually exclusive group for main actions
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create-env", action="store_true", help="Create a default .env file.")
    group.add_argument("--setup", action="store_true", help="Clean everything and setup everything.")
    group.add_argument("--create-admin", action="store_true", help="Create an admin account (boss).")
    group.add_argument("--create-photo-booth", action="store_true", help="Create a photo_booth account.")
    group.add_argument("--create-printer", action="store_true", help="Create a printer account.")

    # Parse arguments
    args = parser.parse_args()

    if not args.skip_env:
        # First, check if a .env file exists. If not, create a default one and ask the user to review it.
        if not os.path.exists(".env") or os.path.exists(".env-dev") or args.create_env:
            print("No .env file found. Creating default .env file...")
            create_default_env()
            print("Default .env file created.")
            if args.create_env:
                exit(0)

            input("Please review the .env file (and print-service/.env if needed), then press Enter to continue...")

        # Load environment variables from the .env file
        load_dotenv()

        # check if .env has all the necessary values
        check_dotenv(True)

    # Retrieve configuration values
    db_url = os.getenv("MONGODB_URL", "localhost:27017")
    db_root = os.getenv("MONGODB_ADMIN_USER", "root")
    db_pw = os.getenv("MONGODB_ADMIN_PASSWORD", "example")
    db_name = os.getenv("MONGODB_DB_NAME", "photobooth")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    # redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    if args.setup:
        setup(db_url, db_root, db_pw, db_name)
        create_admin(db_url, db_root, db_pw, db_name, "boss", None, True)
        create_photo_booth(db_url, db_root, db_pw, db_name, "photo_booth", None, True)
        printer_pw = generate_password()
        create_printer(db_url, db_root, db_pw, db_name, "printer", printer_pw, False, True)

        # Create the default .env file for the print service
        post_create_default_env(base_url, "printer", printer_pw)
    elif args.create_admin:
        create_admin(db_url, db_root, db_pw, db_name)
    elif args.create_photo_booth:
        create_photo_booth(db_url, db_root, db_pw, db_name)
    elif args.create_printer:
        create_printer(db_url, db_root, db_pw, db_name)
    else:
        print("Invalid mode selected.")

if __name__ == "__main__":
    main()
