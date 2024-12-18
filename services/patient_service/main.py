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
patients_collection = db["patients"]

class Patient(BaseModel):
    name: str
    age: int
    gender: str
    email: str
    medical_history: List[str] = []
    prescriptions: List[str] = []

def validate_object_id(object_id: str):
    try:
        return ObjectId(object_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

@app.post("/patients/", response_model=dict)
def add_patient(patient: Patient):
    result = patients_collection.insert_one(patient.dict())
    return {"id": str(result.inserted_id)}

@app.get("/patients/{patient_id}", response_model=dict)
def get_patient(patient_id: str):
    patient = patients_collection.find_one({"_id": validate_object_id(patient_id)})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient["id"] = str(patient.pop("_id"))
    return patient

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)