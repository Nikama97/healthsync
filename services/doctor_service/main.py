from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from pymongo import MongoClient
from bson import ObjectId
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
doctors_collection = db["doctors"]

class Doctor(BaseModel):
    name: str
    specialty: str
    available_slots: List[str] = []

def validate_object_id(object_id: str):
    try:
        return ObjectId(object_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

@app.post("/doctors/", response_model=dict)
def add_doctor(doctor: Doctor):
    result = doctors_collection.insert_one(doctor.dict())
    return {"id": str(result.inserted_id)}

@app.put("/doctors/{doctor_id}", response_model=dict)
def update_doctor_slots(doctor_id: str, available_slots: List[str]):
    result = doctors_collection.update_one(
        {"_id": validate_object_id(doctor_id)},
        {"$set": {"available_slots": available_slots}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"detail": "Slots updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, reload=True)