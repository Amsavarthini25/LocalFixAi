import mysql.connector
from datetime import datetime, timedelta

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="localfix"
)
cursor = db.cursor(dictionary=True)

cursor.execute("""
SELECT complaint_id FROM complaint_status_history h
WHERE status='Resolved'
AND timestamp < NOW() - INTERVAL 3 DAY
AND complaint_id NOT IN (
  SELECT complaint_id FROM complaint_status_history
  WHERE status='Closed'
)
""")

rows = cursor.fetchall()

for r in rows:
    cursor.execute("""
      INSERT INTO complaint_status_history(complaint_id,status)
      VALUES(%s,'Closed')
    """,(r["complaint_id"],))

db.commit()
