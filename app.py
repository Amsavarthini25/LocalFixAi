import os
import mysql.connector
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from gemini_detector import detect_issue
from flask import Flask, request, render_template, redirect, session, url_for
import hashlib,math
import requests
from db import get_db
import config
from datetime import datetime
import pymysql

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 🔹 DB CONNECTION
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
cursor = db.cursor(dictionary=True)
def verify_recaptcha(token):
    payload = {
        "secret": config.RECAPTCHA_SECRET_KEY,
        "response": token
    }

    r = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data=payload
    )

    return r.json().get("success", False)


# --------------------------------------------------
# HOME
# --------------------------------------------------
@app.route("/")
def home():
   return render_template("home.html")

@app.route("/location")
def location_page():
    return render_template("location.html")

@app.route("/review")
def review_page():
    return render_template("review.html")

@app.route("/success")
def success_page():
    return render_template("success.html")

@app.route("/complaint")
def complaint():
    if "user_id" not in session:
        return redirect("/citizen/signin")  # optional safety

    # Dummy complaint object to prevent UndefinedError
    complaint = {
        "complaint_id": "N/A",
        "issue_type": "",
        "priority": "",
        "current_status": "",
        "estimated_days": None
    }

    return render_template("complaint.html", complaint=complaint)


@app.route("/authority/dashboard")
def authority_dashboard():
    if session.get("role") != "authority":
        return redirect("/")

    fo_id = session.get("user_id")
    department = session.get("department")

    cursor.execute("""
    SELECT 
        c.complaint_id,
        c.issue_type,
        c.priority,
        c.address,
        c.municipality,
        c.city,
        c.state,
        c.created_at,
        u.name AS citizen_name,
        u.phone_no,
        h.status,
        h.updated_by
    FROM complaints c
    JOIN citizens u ON c.user_id = u.citizen_id
    JOIN complaint_status_history h 
      ON h.id = (
            SELECT h2.id
            FROM complaint_status_history h2
            WHERE h2.complaint_id = c.complaint_id
            ORDER BY h2.timestamp DESC
            LIMIT 1
      )
    WHERE c.department = %s
      AND (
            h.status = 'Submitted'
            OR (h.updated_by = %s AND h.status != 'Closed')
          )
    ORDER BY c.created_at DESC
    """, (department, fo_id))

    complaints = cursor.fetchall()

    return render_template(
        "authority_dashboard.html",
        complaints=complaints,
        department=department
    )

@app.route("/citizen/report")
def report():

    if session.get("role") != "citizen":
        return redirect("/")

    return render_template("index.html")










#-------------------------------------------------
# SIGNIN SIGNUP 
#-------------------------------------------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()
@app.route("/citizen_signup", methods=["GET", "POST"])
def citizen_signup():
    error = None

    if request.method == "POST":
        token = request.form.get("g-recaptcha-response")

        if not token or not verify_recaptcha(token):
            return render_template(
                "citizen_signup.html",
                error="Captcha verification failed",
                site_key=config.RECAPTCHA_SITE_KEY
            )

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = hash_password(request.form["password"])

        cursor.execute("""
            INSERT INTO citizens(name,email,password_hash,phone_no)
            VALUES(%s,%s,%s,%s)
        """, (name, email, password, phone))
        db.commit()

        return redirect("/citizen/signin")

    return render_template(
        "citizen_signup.html",
        error=error,
        site_key=config.RECAPTCHA_SITE_KEY
    )



@app.route("/citizen/signin", methods=["GET", "POST"])
def citizen_signin():
    error = None

    if request.method == "POST":
        token = request.form.get("g-recaptcha-response")

        if not token or not verify_recaptcha(token):
            return render_template(
                "citizen_signin.html",
                error="Captcha verification failed",
                site_key=config.RECAPTCHA_SITE_KEY
            )

        email = request.form["email"]
        password = hash_password(request.form["password"])

        cursor.execute("""
            SELECT citizen_id, name FROM citizens
            WHERE email=%s AND password_hash=%s
        """, (email, password))

        user = cursor.fetchone()

        if not user:
            error = "Invalid credentials"
        else:
            session["user_id"] = user["citizen_id"]
            session["role"] = "citizen"
            session["user_name"] = user["name"]

            return redirect(url_for("report"))

    return render_template(
        "citizen_signin.html",
        error=error,
        site_key=config.RECAPTCHA_SITE_KEY
    )




@app.route("/authority/signin", methods=["GET", "POST"])
def authority_signin():
    error = None

    if request.method == "POST":
        token = request.form.get("g-recaptcha-response")

        # Verify captcha
        if not token or not verify_recaptcha(token):
            return render_template(
                "authority_signin.html",
                error="Captcha verification failed",
                site_key=config.RECAPTCHA_SITE_KEY
            )

        email = request.form["email"]
        password = hash_password(request.form["password"])

        # Fetch authority including email
        cursor.execute("""
            SELECT authority_id, name, department, email
            FROM authorities
            WHERE email=%s AND password_hash=%s
        """, (email, password))

        user = cursor.fetchone()

        if not user:
            error = "Invalid credentials"
        else:
            # Store necessary session variables
            session["user_id"] = user["authority_id"]
            session["role"] = "authority"
            session["user_name"] = user["name"]
            session["department"] = user["department"]
            session["authority_email"] = user["email"]  # <-- new, fixes KeyError

            return redirect(url_for("authority_dashboard"))

    return render_template(
        "authority_signin.html",
        error=error,
        site_key=config.RECAPTCHA_SITE_KEY
    )




@app.route("/admin/signin", methods=["GET","POST"])
def admin_signin():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT admin_id, name
            FROM admins
            WHERE email=%s AND password_hash=%s
        """, (email, password))

        user = cursor.fetchone()

        if not user:
            error = "Invalid credentials"
        else:
            session["user_id"] = user["admin_id"]
            session["role"] = "admin"
            session["user_name"] = user["name"]
            return redirect("/admin/dashboard")

    return render_template("admin_signin.html", error=error)




@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role")!="admin":
        return redirect("/signin")
    return render_template("admin_dashboard.html")



@app.route("/admin/add_authority", methods=["GET","POST"])
def add_authority():
    if session.get("role") != "admin":
        return redirect("/signin")

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = hash_password(request.form["password"])
        role = request.form["role"]
        department = request.form.get("department")
        municipality = request.form.get("municipality")
        phone = request.form["phone"]

        # --- Governance Rules ---
        if role in ["Assistant Commissioner", "Commissioner"]:
            department = None

        if role == "Commissioner":
            municipality = None

        cursor.execute("""
            INSERT INTO authorities
            (name, email, password_hash, department, role, municipality, phone_no)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (name, email, password, department, role, municipality, phone))

        db.commit()
        return redirect("/admin/dashboard")

    return render_template("add_authority.html")





@app.route("/citizen/dashboard")
def citizen_dash():

    if session.get("role") != "citizen":
        return redirect("/")

    return render_template("citizen_notifications.html")


@app.route("/authority/dashboard")
def authority_dash():
    if session.get("role")!="authority":
        return redirect("/signin")
    return "Authority Dashboard"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/authority/override-eta",methods=["POST"])
def override_eta():
    data=request.json

    cursor.execute("""
      UPDATE complaint_sla_assignment
      SET final_estimated_days=%s, overridden=1, override_reason=%s
      WHERE complaint_id=%s
    """,(data["final_days"],data["reason"],data["complaint_id"]))

    cursor.execute("""
      UPDATE complaints SET estimated_days=%s WHERE complaint_id=%s
    """,(data["final_days"],data["complaint_id"]))

    db.commit()
    return jsonify({"status":"ok"})



@app.route("/authority/sla-impacting")
def sla_impacting_complaints():
    if session.get("role") != "authority":
        return redirect("/")

    department = session["department"]

    cursor.execute("""
        SELECT c.complaint_id, c.issue_type, c.priority, c.created_at
        FROM complaints c
        WHERE c.department=%s
          AND c.priority='High'
          AND c.complaint_id NOT IN (
              SELECT complaint_id
              FROM complaint_status_history
              WHERE status IN ('Resolved','Closed')
          )
        ORDER BY c.created_at ASC
    """, (department,))

    complaints = cursor.fetchall()

    return render_template(
        "authority_dashboard.html",
        complaints=complaints,
        department=department,
        sla_view=True
    )


# --------------------------------------------------
# STEP 1–3 : IMAGE + TEXT → GEMINI → DB INSERT
# --------------------------------------------------
# --------------------------------------------------
# STEP 1–3 : IMAGE + TEXT → GEMINI → DB INSERT
# --------------------------------------------------
@app.route("/analyze", methods=["POST"])
def analyze():
    image = request.files["image"]
    description = request.form.get("description")

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)

    ai_output = detect_issue(image_path, description)

    if not ai_output.get("issue_type"):
        return jsonify({"error": "AI detection failed. Please retry."}), 400

    user_id = 1  # demo user

    # ✅ INSERT (NO complaint_id)
    cursor.execute("""
        INSERT INTO complaints (
            user_id,
            issue_type,
            department,
            priority,
            estimated_days
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        user_id,
        ai_output["issue_type"],
        ai_output["department"],
        ai_output["priority"],
        None
    ))

    # ✅ GET auto-generated complaint_id
    complaint_id = cursor.lastrowid

    # ✅ INSERT initial status
    cursor.execute("""
        INSERT INTO complaint_status_history (
            complaint_id, status, updated_by
        )
        VALUES (%s, %s, %s)
    """, (
        complaint_id,
        "Submitted",
        user_id
    ))

    db.commit()

    return jsonify({
        "complaint_id": complaint_id,
        "ai_result": ai_output
    })




# --------------------------------------------------
# STEP 4 : LOCATION + MUNICIPALITY → DB UPDATE
# --------------------------------------------------
@app.route("/receive", methods=["POST"])
def receive():
    data = request.json

    cursor.execute("""
        UPDATE complaints
        SET latitude=%s,
            longitude=%s,
            address=%s,
            municipality=%s,
            city=%s,
            state=%s
        WHERE complaint_id=%s
    """, (
        data["latitude"],
        data["longitude"],
        data["address"],
        data["municipality"],
        data["city"],
        data["state"],
        data["complaint_id"]
    ))

    db.commit()
    return jsonify({"status": "Location updated"})

@app.route("/submit-complaint", methods=["POST"])
def submit_complaint():
    # insert into DB
    cursor.execute(query, values)
    db.commit()

    complaint_id = cursor.lastrowid  # VERY IMPORTANT

    return jsonify({
        "status": "success",
        "complaint_id": complaint_id
    })


#-----------------------------------------------------
# SYSTEM ETA CALCULATION 
#-----------------------------------------------------

def calculate_system_eta(department, priority):
    # 1️⃣ Get daily capacity
    cursor.execute("""
        SELECT daily_capacity
        FROM department_capacity
        WHERE department=%s
    """, (department,))
    cap = cursor.fetchone()

    if not cap:
        return 5  # fallback

    daily_capacity = cap["daily_capacity"]

    # 2️⃣ Count pending complaints
    cursor.execute("""
        SELECT COUNT(*) AS pending
        FROM complaints
        WHERE department=%s
          AND complaint_id NOT IN (
              SELECT complaint_id
              FROM complaint_status_history
              WHERE status IN ('Resolved','Closed')
          )
    """, (department,))

    pending = cursor.fetchone()["pending"]

    # 3️⃣ Base ETA
    base_eta = max(1, math.ceil(pending / daily_capacity))

    # 4️⃣ Priority weight
    weight = {
        "High": 0.6,
        "Medium": 1,
        "Low": 1.3
    }.get(priority, 1)

    return max(1, math.ceil(base_eta * weight))


@app.route("/authority/complaint/<int:complaint_id>")
def authority_complaint_detail(complaint_id):

    if session.get("role") != "authority":
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    # Complaint + citizen email + current status + ETA
    cursor.execute("""
        SELECT 
            c.*,
            ci.email AS citizen_email,

            (SELECT status 
             FROM complaint_status_history 
             WHERE complaint_id = c.complaint_id
             ORDER BY timestamp DESC LIMIT 1) AS current_status,

            (SELECT final_estimated_days
             FROM complaint_sla_assignment
             WHERE complaint_id = c.complaint_id) AS estimated_days

        FROM complaints c
        JOIN citizens ci ON c.user_id = ci.citizen_id
        WHERE c.complaint_id=%s
    """,(complaint_id,))
    complaint = cursor.fetchone()

    # Status history with formatted date
    cursor.execute("""
    SELECT status,
           DATE_FORMAT(timestamp,'%%d-%%m-%%Y %%h:%%i %%p') AS datetime
    FROM complaint_status_history
    WHERE complaint_id=%s
    ORDER BY timestamp
""",(complaint_id,))
    history = cursor.fetchall()


    return render_template(
        "authority_complaint_detail.html",
        complaint=complaint,
        history=history
    )



@app.route("/authority/eta/<int:complaint_id>")
def get_or_create_eta(complaint_id):

    # 0️⃣ Fetch complaint (basic validation)
    cursor.execute("SELECT * FROM complaints WHERE complaint_id=%s",(complaint_id,))
    c = cursor.fetchone()

    if not c:
        return jsonify({"error":"Complaint not found"}),404

    # 1️⃣ 🔒 BLOCK if already closed
    cursor.execute("""
        SELECT status FROM complaint_status_history
        WHERE complaint_id=%s
        ORDER BY timestamp DESC LIMIT 1
    """,(complaint_id,))
    s = cursor.fetchone()

    if s and s["status"] in ("Resolved","Closed"):
        return jsonify({"error":"Complaint already closed"}),400


    # 2️⃣ Check SLA
    cursor.execute("""
        SELECT * FROM complaint_sla_assignment
        WHERE complaint_id=%s
    """,(complaint_id,))
    sla = cursor.fetchone()


    # 3️⃣ Create SLA if missing
    if not sla:
        system_eta = calculate_system_eta(c["department"], c["priority"])

        cursor.execute("""
            INSERT INTO complaint_sla_assignment
            (complaint_id, department, priority_at_time,
             system_estimated_days, final_estimated_days, overridden)
            VALUES (%s,%s,%s,%s,%s,FALSE)
        """, (
            complaint_id,
            c["department"],
            c["priority"],
            system_eta,
            system_eta
        ))

        cursor.execute("""
            UPDATE complaints
            SET estimated_days=%s
            WHERE complaint_id=%s
        """,(system_eta, complaint_id))

        db.commit()

        return jsonify({
            "eta": system_eta,
            "system_eta": system_eta,
            "overridden": False
        })


    # 4️⃣ Return existing SLA
    return jsonify({
        "eta": sla["final_estimated_days"],
        "system_eta": sla["system_estimated_days"],
        "overridden": sla["overridden"]
    })




@app.route("/authority/update-eta", methods=["POST"])
def update_eta():

    if session.get("role") != "authority":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    cid = data["complaint_id"]

    # update SLA
    cursor.execute("""
        UPDATE complaint_sla_assignment
        SET final_estimated_days=%s,
            overridden=%s,
            override_reason=%s,
            overridden_by=%s,
            overridden_at=NOW()
        WHERE complaint_id=%s
    """, (
        data["eta"],
        data["overridden"],
        data.get("reason"),
        session["user_id"],
        cid
    ))

    cursor.execute("""
        UPDATE complaints SET estimated_days=%s WHERE complaint_id=%s
    """,(data["eta"], cid))


    # 🔥 get latest status
    cursor.execute("""
        SELECT status FROM complaint_status_history
        WHERE complaint_id=%s
        ORDER BY timestamp DESC LIMIT 1
    """,(cid,))
    row = cursor.fetchone()

    current_status = row["status"] if row else "Submitted"

    # 🔥 Auto-assign only once
    if current_status == "Submitted":
        cursor.execute("""
            INSERT INTO complaint_status_history(complaint_id,status,updated_by)
            VALUES(%s,'Assigned',%s)
        """,(cid, session["user_id"]))

    db.commit()
    return jsonify({"status":"updated"})


import config
def get_db_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )



def calculate_system_eta(department, target_priority):

    # 1️⃣ Department daily capacity
    cursor.execute("""
        SELECT daily_capacity FROM department_capacity
        WHERE department=%s
    """,(department,))
    cap = cursor.fetchone()
    daily_capacity = cap["daily_capacity"] if cap else 3

    # 2️⃣ Fetch all active complaints with latest status
    cursor.execute("""
        SELECT c.priority,
               (
                   SELECT status
                   FROM complaint_status_history
                   WHERE complaint_id=c.complaint_id
                   ORDER BY timestamp DESC
                   LIMIT 1
               ) AS current_status
        FROM complaints c
        WHERE c.department=%s
          AND c.complaint_id NOT IN (
              SELECT complaint_id
              FROM complaint_status_history
              WHERE status IN ('Resolved','Closed')
          )
    """,(department,))
    complaints = cursor.fetchall()

    # 3️⃣ status time mapping
    status_weight = {
        "Submitted":1.0,
        "Assigned":0.8,
        "Visited":0.6,
        "In_Progress":0.3
    }

    # 4️⃣ priority weight
    priority_weight = {"High":1.5,"Medium":1.0,"Low":0.6}

    total_load = 0
    for c in complaints:
        sw = status_weight.get(c["current_status"],1)
        pw = priority_weight.get(c["priority"],1)
        total_load += sw * pw

    # 5️⃣ ETA for new complaint
    target_weight = priority_weight.get(target_priority,1)
    effective_load = total_load / target_weight

    eta = max(1, math.ceil(effective_load / daily_capacity))
    return eta


@app.route("/authority/update-status", methods=["POST"])
def update_status():
    if session.get("role") != "authority":
        return jsonify({"error":"unauthorized"}),403

    data = request.json
    complaint_id = data["complaint_id"]
    new_status = data["status"]

    cursor.execute("""
        INSERT INTO complaint_status_history(complaint_id,status,updated_by)
        VALUES(%s,%s,%s)
    """,(complaint_id,new_status,session["user_id"]))
    db.commit()

    return jsonify({"status":"ok"})


@app.route("/track", methods=["GET", "POST"])
def track():

    if session.get("role") != "citizen":
        return redirect("/")

    if request.method == "POST":

        cid = request.form.get("complaint_id")

        if not cid:
            return render_template("track.html", error="Complaint ID required")

        cursor.execute("""
            SELECT *
            FROM complaints
            WHERE complaint_id=%s
              AND user_id=%s
        """, (cid, session["user_id"]))

        complaint = cursor.fetchone()

        if not complaint:
            return render_template("track.html", error="Invalid Complaint ID")

        cursor.execute("""
    SELECT status,
           DATE_FORMAT(timestamp,'%%d-%%m-%%Y %%h:%%i %%p') AS datetime
    FROM complaint_status_history
    WHERE complaint_id=%s
    ORDER BY timestamp
""", (cid,))
        history = cursor.fetchall()


        # 🔥 FETCH ETA IN-CHARGE AUTHORITY
        cursor.execute("""
            SELECT a.name, a.email, a.department
            FROM complaint_sla_assignment s
            JOIN authorities a
              ON a.authority_id = s.overridden_by
            WHERE s.complaint_id = %s
            ORDER BY s.overridden_at DESC
            LIMIT 1
        """, (cid,))
        authority = cursor.fetchone()

        return render_template(
            "track.html",
            complaint=complaint,
            history=history,
            authority=authority,
            show_result=True
        )

    return render_template("track.html")


@app.route("/citizen/profile")
def citizen_profile():
    # Example: fetch user profile details
    user = {"name": session.get("user_name", "Citizen")}
    return render_template("citizen_profile.html", user=user)

# ================= CITIZEN SETTINGS =================
@app.route("/citizen/settings")
def citizen_settings():
    # Example: fetch settings for the user
    settings = {}  # Replace with DB query if needed
    return render_template("citizen_settings.html", settings=settings)


# ================= LOGIN (example) =================
@app.route("/login", methods=["GET", "POST"])
def login():
    # Simple placeholder login
    if "user_name" not in session:
        session["user_name"] = "Amsavarthini"
    return redirect(url_for("citizen_signin"))


@app.route("/authority/notifications")
def authority_notifications():
    if session.get("role") != "authority":
        return redirect("/")

    email = session.get("authority_email")

    cursor.execute("""
        SELECT sel.id, sel.complaint_id, sel.escalation_level,
               sel.notified_at, sel.is_read
        FROM sla_escalation_log sel
        WHERE sel.notified_to=%s
        ORDER BY sel.notified_at DESC
    """, (email,))

    notifications = cursor.fetchall()
    return render_template("authority_notifications.html", notifications=notifications)

#notificationss

@app.route("/authority/notifications-json")
def notifications_json():
    cursor.execute("""
        SELECT * FROM sla_escalation_log
        WHERE notified_to=(SELECT email FROM authorities WHERE authority_id=%s)
        ORDER BY notified_at DESC
    """, (session["user_id"],))
    return jsonify(cursor.fetchall())

@app.route("/authority/notifications/read_all", methods=["POST"])
def mark_notifications_read():
    email = session.get("authority_email")

    cursor.execute("""
        UPDATE sla_escalation_log
        SET is_read=1
        WHERE notified_to=%s
    """, (email,))
    db.commit()

    return redirect(url_for("authority_notifications"))







@app.route("/citizen/notifications")
def citizen_notifications():
    if session.get("role") != "citizen":
        return redirect("/login")  # Only citizens can see notifications

    user_id = session.get("user_id")  # citizen's user_id

    cursor = db.cursor(dictionary=True)
    
    # Fetch all status updates for complaints submitted by this citizen
    cursor.execute("""
        SELECT csh.id, csh.complaint_id, csh.status, csh.timestamp, a.name AS updated_by_name
        FROM complaint_status_history csh
        JOIN complaints c ON csh.complaint_id = c.complaint_id
        LEFT JOIN authorities a ON csh.updated_by = a.authority_id
        WHERE c.user_id = %s
        ORDER BY csh.timestamp DESC
    """, (user_id,))

    notifications = cursor.fetchall()

    return render_template("citizen_notifications.html", notifications=notifications)

@app.route("/api/citizen/notifications")
def api_citizen_notifications():
    if session.get("role") != "citizen":
        return jsonify([])

    user_id = session.get("user_id")
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT csh.id, csh.complaint_id, csh.status, csh.timestamp, a.name AS updated_by_name
        FROM complaint_status_history csh
        JOIN complaints c ON csh.complaint_id = c.complaint_id
        LEFT JOIN authorities a ON csh.updated_by = a.authority_id
        WHERE c.user_id = %s
        ORDER BY csh.timestamp DESC
        LIMIT 20
    """, (user_id,))
    notifications = cursor.fetchall()

    # Convert timestamp to string for JSON
    for n in notifications:
        n['timestamp'] = n['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(notifications)

# =========================
# PUBLIC TRANSPARENCY DASHBOARD
# =========================
@app.route("/public_dashboard")
def public_dashboard():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Total complaints
    cur.execute("SELECT COUNT(*) AS total FROM complaints")
    total = cur.fetchone()["total"]

    # Complaints by priority
    cur.execute("""
        SELECT priority, COUNT(*) AS count
        FROM complaints
        GROUP BY priority
    """)
    priority_data = cur.fetchall()

    # Complaints by department
    cur.execute("""
        SELECT department, COUNT(*) AS count
        FROM complaints
        GROUP BY department
    """)
    dept_data = cur.fetchall()

    # Recent complaints
    cur.execute("""
        SELECT issue_type, municipality, created_at
        FROM complaints
        ORDER BY created_at DESC
        LIMIT 6
    """)
    recent = cur.fetchall()

    # Resolved complaints count
    cur.execute("""
        SELECT COUNT(*) AS resolved
        FROM complaint_status_history
        WHERE status = 'Resolved'
    """)
    resolved = cur.fetchone()["resolved"]

    conn.close()

    return render_template(
        "public_dashboard.html",
        total=total,
        priority_data=priority_data,
        dept_data=dept_data,
        recent=recent,
        resolved=resolved
    )

@app.route("/admin/remove_authority")
def remove_authority():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM authorities")
    authorities = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "remove_authority.html",
        authorities=authorities
    )
@app.route("/admin/delete_authority/<int:authority_id>")
def delete_authority(authority_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM authorities WHERE authority_id = %s",
        (authority_id,)
    )

    db.commit()
    cursor.close()
    db.close()

    return redirect("/admin/remove_authority")
@app.route("/admin/manage_authority")
def manage_authority():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM authorities")
    authorities = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "manage_authority.html",
        authorities=authorities
    )
@app.route("/admin/edit_authority/<int:authority_id>")
def edit_authority(authority_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM authorities WHERE authority_id=%s",
        (authority_id,)
    )
    authority = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "edit_authority.html",
        authority=authority
    )

@app.route("/admin/view_complaints")
def admin_complaints():
    if "admin_id" not in session:
        return redirect("/admin/signin")

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT c.*, cs.status
        FROM complaints c
        LEFT JOIN complaint_status_history cs
        ON c.complaint_id = cs.complaint_id
        ORDER BY c.created_at DESC
    """)

    return render_template("admin_complaints.html", complaints=cur.fetchall())
@app.route("/admin/update_authority/<int:authority_id>", methods=["POST"])
def update_authority(authority_id):
    department = request.form["department"]
    municipality = request.form["municipality"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE authorities
        SET department=%s, municipality=%s
        WHERE authority_id=%s
    """, (department, municipality, authority_id))

    db.commit()
    cursor.close()
    db.close()

    return redirect("/admin/manage_authority")

@app.route("/admin/system_logs")
def system_logs():
    if "admin_id" not in session:
        return redirect("/admin/signin")

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT * FROM complaint_status_history
        ORDER BY timestamp DESC
    """)

    return render_template("system_logs.html", logs=cur.fetchall())

from apscheduler.schedulers.background import BackgroundScheduler
from sla_engine import run_sla_engine

scheduler = BackgroundScheduler()
scheduler.add_job(run_sla_engine, 'interval', minutes=1, max_instances=1, coalesce=True)





# --------------------------------------------------
if __name__ == "__main__":
    scheduler.start()
    app.run(debug=True)
