import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, Optional, Tuple
import uuid
import time

import bcrypt

from db_connection import MongoDBConnection
from user import User


SESSION_DURATION_SECONDS = 60 * 60 * 24


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class Session:
    user: User
    expiration_date: datetime
    _logout_callback_toremove_from_session_manager: Callable[["Session"], None]
    _expiration_callback: Optional[Callable[["Session"], None]] = None
    mongodb_connection: Optional[MongoDBConnection] = None
    creation_date: datetime = field(default_factory=datetime.now)
    _id: str = field(default_factory=lambda: f"SESSION-{uuid.uuid4()}")
    _expiration_task: Optional[asyncio.Task] = None  # Reference to the async task

    @property
    def status(self) -> Status:
        if self.mongodb_connection is None:
            return Status.INACTIVE
        return Status.ACTIVE

    async def logout(self) -> None:
        if self.status == Status.ACTIVE:
            if self.mongodb_connection:
                self.mongodb_connection.close()
                self.mongodb_connection = None

            self._logout_callback_toremove_from_session_manager(self)

            # Cancel the expiration worker if it's still running
            if self._expiration_task and not self._expiration_task.done():
                self._expiration_task.cancel()

            if self._expiration_callback:
                self._expiration_callback(self)

    async def is_admin(self) -> bool:
        if self.status == Status.INACTIVE:
            return False
        return "admin" in self.user.roles or "boss" in self.user.roles


class SessionManager:
    _instance: Optional["SessionManager"] = None

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()  # Use asyncio.Lock for async safety

    def __new__(cls, *args: Tuple, **kwargs: Dict) -> "SessionManager":
        if not cls._instance:
            cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance

    async def _expire_session(self, session: Session) -> None:
        """Handles session expiration asynchronously."""
        try:
            await asyncio.sleep(SESSION_DURATION_SECONDS)  # Wait until session expires
            await session.logout()
            print(f"Session {session._id} expired.")
        except asyncio.CancelledError:
            # Task was cancelled before expiration (user logged out manually)
            print(f"Session {session._id} logout cancelled before expiration.")

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash the given password using bcrypt. Generates a new salt if not provided.
        Returns a tuple of (hashed_password, salt).
        """
        if salt is None:
            salt_bytes = bcrypt.gensalt()
            salt = salt_bytes.decode()
        hashed = bcrypt.hashpw(password.encode(), salt.encode()).decode()
        return hashed, salt

    async def login(self, 
                        db_connection: MongoDBConnection, 
                        username: str, 
                        password: str, 
                        expiration_callback: Optional[Callable[["Session"], None]] = None
                    ) -> Session:
        """Handles user login and session creation."""
        user_data = User.db_find_by_username(db_connection, username)

        salt = user_data.password_salt
        hashed, _ = self.hash_password(password, salt)
        if hashed != user_data.password_hash:
            raise ValueError("Incorrect password")

        # Try to login to the DB
        new_db_connection = MongoDBConnection(
            mongo_uri=db_connection.mongo_uri,
            user=username,
            password=password,
            db_name=db_connection.db_name
        )

        async def _async_logout_user(session: Session) -> None:
            """Actual async function to remove session safely within async context."""
            async with self._lock:
                print(f"Logging out user {session.user.username} from session {session._id}")
                self._sessions.pop(session._id, None)

        def logout_user(session: Session) -> None:
            """Synchronous logout function as required by Session."""
            asyncio.create_task(_async_logout_user(session))


        # save new date
        user_data.last_login = datetime.now()
        user_data.db_update(db_connection)

        # Create a session for the user
        new_session = Session(
            user = user_data,
            expiration_date=datetime.now() + timedelta(seconds=SESSION_DURATION_SECONDS),
            _logout_callback_toremove_from_session_manager=logout_user,
            _expiration_callback=expiration_callback,
            mongodb_connection=new_db_connection
        )

        async with self._lock:
            self._sessions[new_session._id] = new_session

        # Create an async expiration task and store a reference
        new_session._expiration_task = asyncio.create_task(self._expire_session(new_session))

        return new_session

    async def get_sessions(self) -> Dict[str, Session]:
        async with self._lock:
            return self._sessions.copy()

    async def get_session(self, session_id: str) -> Optional[Session]:
        async with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]
            return None






async def test_session_manager() -> None:
    MONGODB_URI = "localhost:27017"
    MONGODB_DB_NAME = "photo_booth"
    MONGODB_ADMIN_USER = "root"
    MONGODB_ADMIN_PASSWORD = "example"



    admin_db = MongoDBConnection(
        mongo_uri=MONGODB_URI,
        user=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        db_name=MONGODB_DB_NAME
    )

    session_manager = SessionManager()

    def expiration_callback(session: Session) -> None:
        print(f"Session {session._id} expired!")

    # Test login
    session = await session_manager.login(
        admin_db,
        username=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        expiration_callback=expiration_callback
    )
    print(f"Created session: {session._id}, Status: {session.status}")

    # Check if session is active
    assert session.status == Status.ACTIVE

    # Retrieve sessions
    sessions = await session_manager.get_sessions()
    print(f"Active sessions: {list(sessions.keys())}")
    assert session._id in sessions

    await asyncio.sleep(15)

    # Test logout
    await session.logout()
    print(f"Session {session._id} logged out, Status: {session.status}")
    assert session.status == Status.INACTIVE

    # Ensure session is removed
    sessions = await session_manager.get_sessions()
    assert session._id not in sessions
    print("Session successfully removed from session manager.")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_session_manager())