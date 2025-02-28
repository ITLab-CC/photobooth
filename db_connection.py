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