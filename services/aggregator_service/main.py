# services/aggregator_service/main.py
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import MongoClient
import psycopg2
import logging
from typing import List, Dict
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class DataAggregator:
    def __init__(self):
        # MongoDB connection
        self.mongo_client = MongoClient(os.getenv('MONGO_URL'))
        self.mongo_db = self.mongo_client['health']
        self.appointments_collection = self.mongo_db["appointments"]

        # Redshift connection
        self.redshift_conn = psycopg2.connect(
            dbname=os.getenv('REDSHIFT_DB', 'healthsync'),
            host=os.getenv('REDSHIFT_HOST'),
            port=int(os.getenv('REDSHIFT_PORT', '5439')),
            user=os.getenv('REDSHIFT_USER'),
            password=os.getenv('REDSHIFT_PASSWORD')
        )

        self.create_redshift_tables()

    def create_redshift_tables(self):
        """Create necessary tables in Redshift if they don't exist"""
        print("im here")


        try:
            print("im here try")
            cursor = self.redshift_conn.cursor()
            # Table for appointments per doctor
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS doctor_appointments_agg (
                    doctor_id VARCHAR(255),
                    doctor_name VARCHAR(255),
                    specialty VARCHAR(255),
                    appointment_count INTEGER,
                    aggregation_date DATE,
                    PRIMARY KEY (doctor_id, aggregation_date)
                );
            """)
        except:
            print("gg")


        # Table for appointment frequency
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointment_frequency_agg (
                date DATE,
                appointment_count INTEGER,
                aggregation_date DATE,
                PRIMARY KEY (date, aggregation_date)
            );
        """)

        # Table for symptoms by specialty
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symptoms_by_specialty_agg (
                specialty VARCHAR(255),
                symptom VARCHAR(255),
                occurrence_count INTEGER,
                aggregation_date DATE,
                PRIMARY KEY (specialty, symptom, aggregation_date)
            );
        """)

        self.redshift_conn.commit()
        cursor.close()

    def aggregate_doctor_appointments(self) -> List[Dict]:
        """Aggregate appointments per doctor"""
        # First, get all appointments grouped by doctor_id
        pipeline = [
            {
                "$group": {
                    "_id": "$doctor_id",
                    "appointment_count": {"$sum": 1}
                }
            }
        ]

        appointments_result = list(self.mongo_db.appointments.aggregate(pipeline))

        # Then, get doctor information and combine the data
        aggregated_data = []
        for appointment in appointments_result:
            doctor_id = appointment["_id"]
            try:
                # Find the doctor information
                doctor = self.mongo_db.doctors.find_one({"_id": ObjectId(doctor_id)})
                if doctor:
                    aggregated_data.append({
                        "doctor_id": str(doctor_id),
                        "doctor_name": doctor.get("name", "Unknown"),
                        "specialty": doctor.get("specialty", "Unknown"),
                        "appointment_count": appointment["appointment_count"]
                    })
                else:
                    # Handle case where doctor is not found
                    logger.warning(f"Doctor not found for ID: {doctor_id}")
                    aggregated_data.append({
                        "doctor_id": str(doctor_id),
                        "doctor_name": "Unknown",
                        "specialty": "Unknown",
                        "appointment_count": appointment["appointment_count"]
                    })
            except Exception as e:
                logger.error(f"Error processing doctor_id {doctor_id}: {str(e)}")
                continue

        print("aggregated_data",aggregated_data)
        return aggregated_data

    def aggregate_appointment_frequency(self) -> List[Dict]:
        """Aggregate appointment frequency over time"""
        pipeline = [
            {
                "$group": {
                    "_id": "$date",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        result = list(self.mongo_db.appointments.aggregate(pipeline))
        return [
            {
                "date": r["_id"],
                "appointment_count": r["count"]
            }
            for r in result
        ]

    def aggregate_symptoms_by_specialty(self) -> List[Dict]:
        """Aggregate symptoms categorized by specialty"""
        pipeline = [
            # Convert string doctor_id to ObjectId
            {
                "$addFields": {
                    "doctor_object_id": {
                        "$toObjectId": "$doctor_id"
                    }
                }
            },
            # Lookup using the converted ObjectId
            {
                "$lookup": {
                    "from": "doctors",
                    "localField": "doctor_object_id",
                    "foreignField": "_id",
                    "as": "doctor_info"
                }
            },
            # Unwind arrays
            {"$unwind": "$doctor_info"},
            {"$unwind": "$symptoms"},
            # Group by specialty and symptom
            {
                "$group": {
                    "_id": {
                        "specialty": "$doctor_info.specialty",
                        "symptom": "$symptoms"
                    },
                    "count": {"$sum": 1}
                }
            },
            # Sort by count descending
            {"$sort": {"count": -1}},
            # Reshape the output
            {
                "$project": {
                    "_id": 0,
                    "specialty": "$_id.specialty",
                    "symptom": "$_id.symptom",
                    "occurrence_count": "$count"
                }
            }
        ]

        try:
            result = list(self.mongo_db.appointments.aggregate(pipeline))
            print("result_symptoms",result)
            return result
        except Exception as e:
            logger.error(f"Error in symptoms aggregation: {str(e)}")
            return []

    def save_to_redshift(self, data: List[Dict], table_name: str, columns: List[str]):
        """Save aggregated data to Redshift"""
        cursor = self.redshift_conn.cursor()

        # Create values string for the INSERT query
        values_template = "(" + ",".join(["%s"] * len(columns)) + ")"

        # Prepare the INSERT query
        query = f"""
            INSERT INTO {table_name} 
            ({','.join(columns)}) 
            VALUES {values_template}
        """

        # Insert data
        for item in data:
            values = [item[col] for col in columns[:-1]]  # Exclude aggregation_date
            values.append(datetime.now().date())  # Add aggregation_date
            cursor.execute(query, values)

        self.redshift_conn.commit()
        cursor.close()

    def run_aggregation(self):
        """Run all aggregations and save to Redshift"""
        try:
            logger.info("Starting data aggregation")

            # Aggregate and save doctor appointments
            doctor_appointments = self.aggregate_doctor_appointments()
            self.save_to_redshift(
                doctor_appointments,
                "doctor_appointments_agg",
                ["doctor_id", "doctor_name", "specialty", "appointment_count", "aggregation_date"]
            )

            # Aggregate and save appointment frequency
            appointment_freq = self.aggregate_appointment_frequency()
            self.save_to_redshift(
                appointment_freq,
                "appointment_frequency_agg",
                ["date", "appointment_count", "aggregation_date"]
            )

            # Aggregate and save symptoms by specialty
            symptoms_specialty = self.aggregate_symptoms_by_specialty()
            self.save_to_redshift(
                symptoms_specialty,
                "symptoms_by_specialty_agg",
                ["specialty", "symptom", "occurrence_count", "aggregation_date"]
            )

            logger.info("Data aggregation completed successfully")

        except Exception as e:
            logger.error(f"Error during aggregation: {str(e)}")
            raise

if __name__ == "__main__":
    aggregator = DataAggregator()
    aggregator.run_aggregation()