import mysql.connector

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Amsavarthu@2007",
        database="civic_complaints"
    )
