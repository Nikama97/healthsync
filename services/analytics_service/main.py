from fastapi import FastAPI
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Setup
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "health")
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
appointments_collection = db["appointments"]

@app.get("/analytics/appointments-per-doctor", response_model=dict)
def appointments_per_doctor():
    pipeline = [
        {"$group": {"_id": "$doctor_id", "count": {"$sum": 1}}}
    ]
    result = list(appointments_collection.aggregate(pipeline))
    return {"data": [{"doctor_id": r["_id"], "count": r["count"]} for r in result]}

@app.get("/analytics/appointment-frequency", response_model=dict)
def appointment_frequency():
    pipeline = [
        {"$group": {"_id": "$date", "count": {"$sum": 1}}}
    ]
    result = list(appointments_collection.aggregate(pipeline))
    return {"data": [{"date": r["_id"], "count": r["count"]} for r in result]}

@app.get("/analytics/common-symptoms", response_model=dict)
def common_symptoms():
    pipeline = [
        {"$unwind": "$symptoms"},
        {"$group": {"_id": "$symptoms", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    result = list(appointments_collection.aggregate(pipeline))
    return {"data": [{"symptom": r["_id"], "count": r["count"]} for r in result]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004, reload=True)