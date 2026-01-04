from datetime import datetime, timedelta
import mysql.connector

def run_sla_engine():
    # --- Open a new DB connection per run (thread-safe) ---
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Amsavarthu@2007",
        database="civic_complaints",
        autocommit=True
    )
    cursor = db.cursor(dictionary=True)

    now = datetime.now()

    # --- Log SLA engine run for heartbeat ---
    cursor.execute("INSERT INTO sla_engine_run_log VALUES (NULL, NOW())")

    # --- Get latest status for each complaint ---
    cursor.execute("""
        SELECT c.complaint_id, c.priority, c.estimated_days, c.created_at, h.status, c.department
        FROM complaints c
        JOIN (
            SELECT complaint_id, status
            FROM complaint_status_history
            WHERE id IN (
                SELECT MAX(id) FROM complaint_status_history GROUP BY complaint_id
            )
        ) h ON c.complaint_id = h.complaint_id
        WHERE h.status IN ('Submitted','Assigned','Visited')
          AND c.estimated_days IS NOT NULL
    """)
    complaints = cursor.fetchall()

    for c in complaints:
        # --- Calculate arrival deadline ---
        arrival_deadline = c["created_at"] + timedelta(days=c["estimated_days"])
        if now <= arrival_deadline:
            continue  # Not overdue yet

        delay_days = (now - arrival_deadline).days

        # --- Fetch SLA rules for this complaint's priority ---
        cursor.execute("""
            SELECT * FROM sla_rules
            WHERE priority=%s
            ORDER BY escalation_level
        """, (c["priority"],))
        rules = cursor.fetchall()

        for r in rules:
            if delay_days >= r["max_days"]:
                role_clean = r["notify_role"].strip()

                # --- Get authorities depending on role ---
                if role_clean in ["Assistant Commissioner", "Commissioner"]:
                    # Notify all AC / Coms (case-insensitive, ignore extra spaces)
                    cursor.execute("""
                        SELECT email FROM authorities
                        WHERE TRIM(LOWER(role)) = LOWER(%s)
                    """, (role_clean,))
                else:
                    # Field Officer / Engineer → only in same department
                    cursor.execute("""
                        SELECT email FROM authorities
                        WHERE TRIM(role) = %s
                          AND (department = %s OR department IS NULL)
                    """, (role_clean, c["department"]))

                authorities = cursor.fetchall()

                for a in authorities:
                    # --- Insert notification safely, avoid duplicates ---
                    cursor.execute("""
                        INSERT IGNORE INTO sla_escalation_log
                        (complaint_id, escalation_level, notified_to)
                        VALUES (%s, %s, %s)
                    """, (c["complaint_id"], r["escalation_level"], a["email"]))

    cursor.close()
    db.close()