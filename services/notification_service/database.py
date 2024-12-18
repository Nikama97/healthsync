from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# Database configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://eshan:yprexsHcK7ejG2yY@atlascluster.sqtnfv7.mongodb.net")
DB_NAME = os.getenv("DB_NAME", "healthsync")

# Create database connection
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
notification_collection = db["notifications"]

