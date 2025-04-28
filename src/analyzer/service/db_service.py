""":
Module to provide a reusable MongoDB connection service.
"""

import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file relative to the workspace root
# Assuming .db_env is in the /workspace/data directory
dotenv_path = "/workspace/data/.db_env"
load_dotenv(dotenv_path=dotenv_path)


# Get MongoDB connection string from environment variables
MONGO_USER = os.getenv("MONGO_APP_USER")
MONGO_PASSWORD = os.getenv("MONGO_APP_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_DATABASE = os.getenv("MG_DATABASE")

MONGO_APP_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}/{MONGO_DATABASE}?authSource=cfed"
DEFAULT_MONGO_URI = "mongodb://localhost:27017/"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DBService:
    """Singleton class to manage MongoDB connection."""
    _instance = None
    _client = None
    _db = None

    def __new__(cls, mongo_uri=None):
        if cls._instance is None:
            cls._instance = super(DBService, cls).__new__(cls)
            try:
                uri = mongo_uri or MONGO_APP_URI or DEFAULT_MONGO_URI
                cls._client = MongoClient(uri)
                # The ismaster command is cheap and does not require auth.
                cls._client.admin.command('ismaster')
                cls._db = cls._client[MONGO_DATABASE or 'cfed'] # Default to cfed if not specified
                logger.info(f"Successfully connected to MongoDB: {uri.split('@')[-1]}") # Avoid logging credentials

                # Optionally create indexes if needed by the analyzer
                # cls._db.builds.create_index([...])
                # cls._db.plugin_outputs.create_index([...])

            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                cls._instance = None # Reset instance if connection failed
                raise
        return cls._instance

    def get_db(self):
        """Returns the database instance."""
        if self._db is None:
            raise ConnectionError("Database connection not established.")
        return self._db

    def get_collection(self, collection_name):
        """Returns a specific collection from the database."""
        db = self.get_db()
        return db[collection_name]

    def close_connection(self):
        """Closes the MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")
            DBService._instance = None
            DBService._client = None
            DBService._db = None

# Example usage (optional, for testing)
def get_db_connection():
    """Helper function to get a DBService instance."""
    try:
        db_service = DBService()
        return db_service.get_db()
    except Exception as e:
        logger.error(f"Failed to get DB connection: {e}")
        return None

if __name__ == '__main__':
    try:
        db = get_db_connection()
        if db:
            print(f"Connected to database: {db.name}")
            print("Available collections:", db.list_collection_names())
            
            # Example: Accessing collections
            builds_collection = DBService().get_collection('builds')
            plugin_outputs_collection = DBService().get_collection('plugin_outputs')
            print(f"Builds collection count: {builds_collection.count_documents({})}")
            print(f"Plugin outputs collection count: {plugin_outputs_collection.count_documents({})}")

            # Remember to close the connection when done (e.g., on application shutdown)
            DBService().close_connection()
        else:
            print("Could not establish database connection.")
    except Exception as e:
        print(f"An error occurred: {e}") 