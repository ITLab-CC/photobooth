import asyncio
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple
import uuid
import json
import bcrypt

# Async Redis client (install using: pip install redis)
import redis.asyncio as redis

from img_server.db_connection import MongoDBConnection
from img_server.user import User

SESSION_DURATION_SECONDS = 60 * 60 * 24  # 24 hours
SESSION_PREFIX = "session:"


# --- Session and SessionManager Implementation ---
class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class Session:
    user_id: str
    user_name: str
    user_roles: List[str]
    expiration_date: datetime
    creation_date: datetime = field(default_factory=datetime.now)
    _id: str = field(default_factory=lambda: f"SESSION-{uuid.uuid4()}")

    @property
    async def status(self) -> Status:
        # check if the session is still in redis
        if await SessionManager().exists(self._id):
            return Status.ACTIVE
        return Status.INACTIVE


    async def logout(self) -> None:
        """Log out the session by removing it from the session manager."""
        await SessionManager().logout(self._id)


def serialize_session(session: Session) -> str:
    """Convert the session into a JSON string for storage."""
    data = asdict(session)
    # Convert datetime objects to ISO format strings
    data["expiration_date"] = session.expiration_date.isoformat()
    data["creation_date"] = session.creation_date.isoformat()  # New conversion added here
    return json.dumps(data)



def deserialize_session(json_str: str) -> Session:
    """Recreate a Session object from its JSON string representation."""
    data = json.loads(json_str)
    data["expiration_date"] = datetime.fromisoformat(data["expiration_date"])
    data["creation_date"] = datetime.fromisoformat(data["creation_date"])
    return Session(
        user_id=data["user_id"],
        user_name=data["user_name"],
        user_roles=data["user_roles"],
        expiration_date=data["expiration_date"],
        creation_date=data["creation_date"],
        _id=data["_id"],
    )



class SessionManager:
    _instance = None

    def __new__(cls, *args, **kwargs) -> "SessionManager":
        if not cls._instance:
            cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        # Connect to Redis and use a lock for simple async safety.
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.lock = asyncio.Lock()

    async def login(self, db_connection, username: str, password: str) -> Tuple[Session, User]:
        """Authenticate the user and create a session stored in Redis."""
        # Retrieve user data (replace with your real DB query).
        user = User.db_find_by_username(db_connection, username)
        if user is None:
            raise ValueError("User not found")

        # Verify password. (In production, password_hash and salt should be set properly.)
        hashed, _ = User.hash_password(password, user.password_salt)
        if hashed != user.password_hash:
            raise ValueError("Incorrect password")

        # Update last login.
        user.last_login = datetime.now()
        user.db_update(db_connection)

        # Create a new session.
        session = Session(
            user_id=user._id,
            user_name=user.username,
            user_roles=user.roles,
            expiration_date=datetime.now() + timedelta(seconds=SESSION_DURATION_SECONDS)
        )
        async with self.lock:
            await self.redis.set(
                SESSION_PREFIX + session._id, serialize_session(session), ex=SESSION_DURATION_SECONDS
            )
        return session, user

    async def logout(self, session_id: str) -> None:
        """Remove the session from Redis."""
        async with self.lock:
            await self.redis.delete(SESSION_PREFIX + session_id)

    async def exists(self, session_id: str) -> bool:
        """Check if a session exists in Redis."""
        return await self.redis.exists(SESSION_PREFIX + session_id) > 0

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by its ID from Redis."""
        json_str = await self.redis.get(SESSION_PREFIX + session_id)
        if json_str:
            return deserialize_session(json_str)
        return None

    async def get_sessions(self) -> Dict[str, Session]:
        """Retrieve all sessions stored in Redis."""
        sessions: Dict[str, Session] = {}
        keys = await self.redis.keys(SESSION_PREFIX + "*")
        for key in keys:
            json_str = await self.redis.get(key)
            if json_str:
                session = deserialize_session(json_str)
                sessions[session._id] = session
        return sessions


# --- Test the Simplified Session Manager ---
async def test_session_manager() -> None:
    MONGODB_URI = "localhost:27017"
    MONGODB_DB_NAME = "photo_booth"
    MONGODB_ADMIN_USER = "admin"
    MONGODB_ADMIN_PASSWORD = "admin"

    db_connection = MongoDBConnection(
        mongo_uri=MONGODB_URI,
        user=MONGODB_ADMIN_USER,
        password=MONGODB_ADMIN_PASSWORD,
        db_name=MONGODB_DB_NAME,
        admin=True
    )
    session_manager = SessionManager(redis_url="redis://localhost:6379")

    # create user admin if not exists
    User.db_create_collection(db_connection)
    if not User.db_find_by_username(db_connection, MONGODB_ADMIN_USER):
        User.new(
            db_connection=db_connection,
            username=MONGODB_ADMIN_USER,
            password=MONGODB_ADMIN_PASSWORD,
            roles=["admin"]
        )

    # Log in to create a session.
    session = await session_manager.login(db_connection, MONGODB_ADMIN_USER, MONGODB_ADMIN_PASSWORD)
    print(f"Created session: {session._id}, Status: {await session.status}, user_id: {session.user_id}, roles: {session.user_roles}")

    sessions = await session_manager.get_sessions()
    print("Active sessions:", list(sessions.keys()))

    # Log out of the session.
    await session.logout()
    print(f"Session {session._id} status after logout: {await session.status}")

    # Check that the session is removed from Redis.
    sessions = await session_manager.get_sessions()
    print("Active sessions after logout:", list(sessions.keys()))


if __name__ == "__main__":
    asyncio.run(test_session_manager())
