from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import httpx
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

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

NOTIFICATION_SERVICE_URL = "http://127.0.0.1:8004"

class Appointment(BaseModel):
    patient_id: str
    doctor_id: str
    date: str
    time: str
    symptoms: List[str]

def validate_object_id(object_id: str):
    try:
        return ObjectId(object_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

async def get_patient_details(patient_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://127.0.0.1:8001/patients/{patient_id}")
        return response.json()

async def get_doctor_details(doctor_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://127.0.0.1:8002/doctors/{doctor_id}")
        return response.json()

# async def send_appointment_notification(
#         patient_email: str,
#         doctor_name: str,
#         appointment_date: str,
#         appointment_time: str
# ):
#     notification_data = {
#         "recipient_email": patient_email,
#         "subject": "Appointment Confirmation",
#         "content": f"""
# Dear Patient,
#
# Your appointment has been successfully scheduled with Dr. {doctor_name}
# for {appointment_date} at {appointment_time}.
#
# Please arrive 15 minutes before your scheduled time.
#
# Best regards,
# Health Center Team
#         """.strip(),
#         "status": "pending",
#         "created_at": datetime.now().isoformat()
#     }
#
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(
#                 f"{NOTIFICATION_SERVICE_URL}/notifications/send",
#                 json=notification_data
#             )
#             response.raise_for_status()
#         except Exception as e:
#             print(f"Failed to send notification: {str(e)}")

@app.post("/appointments/", response_model=dict)
async def schedule_appointment(
        appointment: Appointment,
        background_tasks: BackgroundTasks
):
    # Get patient and doctor details from respective services
    patient = await get_patient_details(appointment.patient_id)
    doctor = await get_doctor_details(appointment.doctor_id)

    appointment_datetime = f"{appointment.date} {appointment.time}"

    # Schedule the appointment
    result = appointments_collection.insert_one(appointment.dict())

    # Send notification in the background
    # background_tasks.add_task(
    #     send_appointment_notification,
    #     patient.get("email", ""),
    #     doctor.get("name", ""),
    #     appointment.date,
    #     appointment.time
    # )

    return {"id": str(result.inserted_id)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003, reload=True)