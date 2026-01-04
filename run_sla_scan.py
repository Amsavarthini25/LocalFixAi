# run_sla_scan.py
from app import run_sla_scan  # Import the function from your Flask app
import os
import mysql.connector

# 🔹 DB CONNECTION
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
cursor = db.cursor(dictionary=True)
if __name__ == "__main__":
    run_sla_scan()
