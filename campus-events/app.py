# app.py - simple Campus Event Reporting prototype (Flask + SQLite)
from flask import Flask, request, jsonify, g, render_template
import sqlite3, re
import uuid
from datetime import datetime

DB = 'events.db'
app = Flask(__name__)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        db.row_factory = sqlite3.Row
    return db

@app.route("/")
def root():
    return render_template("index.html")

@app.route("/admin")
def admin_portal():
    return render_template("admin.html")

@app.route("/student")
def student_portal():
    return render_template("student.html")

@app.teardown_appcontext
def close_connection(exc):
    db = getattr(g, '_database', None)
    if db:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.executescript("""
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS colleges (college_id TEXT PRIMARY KEY, name TEXT, timezone TEXT);
    CREATE TABLE IF NOT EXISTS students (student_uuid TEXT PRIMARY KEY, college_id TEXT, student_local_id TEXT, name TEXT, email TEXT, department TEXT, year INTEGER, UNIQUE(college_id, student_local_id));
    CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, college_id TEXT, title TEXT, description TEXT, event_type TEXT, start_ts TEXT, end_ts TEXT, location TEXT, capacity INTEGER, status TEXT);
    CREATE TABLE IF NOT EXISTS registrations (registration_id TEXT PRIMARY KEY, event_id TEXT, student_uuid TEXT, registered_at TEXT, status TEXT DEFAULT 'registered', UNIQUE(event_id, student_uuid));
    CREATE TABLE IF NOT EXISTS attendance (attendance_id TEXT PRIMARY KEY, event_id TEXT, student_uuid TEXT, checkin_at TEXT, method TEXT);
    CREATE TABLE IF NOT EXISTS feedback (feedback_id TEXT PRIMARY KEY, event_id TEXT, student_uuid TEXT, rating INTEGER, comments TEXT, submitted_at TEXT, UNIQUE(event_id, student_uuid));
    CREATE TABLE IF NOT EXISTS registrations (registration_id TEXT PRIMARY KEY,event_id TEXT,student_uuid TEXT,registered_at TEXT,status TEXT DEFAULT 'registered', UNIQUE(event_id, student_uuid),FOREIGN KEY(event_id) REFERENCES events(event_id),FOREIGN KEY(student_uuid) REFERENCES students(student_uuid));
    """)
    db.commit()

def now_iso():
    return datetime.utcnow().isoformat() + 'Z'

@app.route('/api/events/<event_id>/register', methods=['POST'])
def register(event_id):
    j = request.json
    student_name = j.get('name')
    student_email = j.get('email')
    college_id = j.get('college_id') or "college-1"

    if not all([student_name, student_email, college_id]):
        return jsonify({"error": "name, email, and college_id are required"}), 400

    db = get_db()
    cur = db.cursor()

    # Check if event exists
    cur.execute("SELECT capacity FROM events WHERE event_id=?", (event_id,))
    event = cur.fetchone()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Check event capacity
    cur.execute("SELECT COUNT(*) as regs FROM registrations WHERE event_id=?", (event_id,))
    reg_count = cur.fetchone()["regs"]
    if reg_count >= event["capacity"]:
        return jsonify({"error": "Event is full"}), 400

    # Check if student exists
    cur.execute("SELECT student_uuid FROM students WHERE email=? AND college_id=?", (student_email, college_id))
    row = cur.fetchone()
    if row:
        student_uuid = row["student_uuid"]
    else:
        student_uuid = str(uuid.uuid4())
        cur.execute("INSERT INTO students (student_uuid, college_id, student_local_id, name, email) VALUES (?, ?, ?, ?, ?)",
                    (student_uuid, college_id, str(uuid.uuid4()), student_name, student_email))
        db.commit()

    # Register student for the event
    try:
        reg_id = str(uuid.uuid4())
        cur.execute("INSERT INTO registrations (registration_id, event_id, student_uuid, registered_at) VALUES (?, ?, ?, ?)",
                    (reg_id, event_id, student_uuid, datetime.utcnow().isoformat() + "Z"))
        db.commit()
        return jsonify({"registration_id": reg_id, "status": "registered"}), 201
    except sqlite3.IntegrityError:
        # Already registered
        cur.execute("SELECT registration_id, status FROM registrations WHERE event_id=? AND student_uuid=?", (event_id, student_uuid))
        row = cur.fetchone()
        return jsonify({"registration_id": row['registration_id'], "status": row['status']}), 200


# Create event
@app.route('/api/events', methods=['POST'])
def create_event():
    j = request.json
    required = ["college_id", "title", "event_type", "start_ts", "end_ts", "location", "capacity"]

    # Check mandatory fields
    for field in required:
        if not j.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    # Validate capacity
    try:
        capacity = int(j["capacity"])
        if capacity <= 0:
            return jsonify({"error": "capacity must be a positive number"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "capacity must be an integer"}), 400

    # Validate start & end times
    try:
        start_dt = datetime.fromisoformat(j["start_ts"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(j["end_ts"].replace("Z", "+00:00"))
    except ValueError:
        return jsonify({"error": "Invalid datetime format. Use ISO 8601 (e.g., 2025-09-20T10:00:00Z)"}), 400

    if end_dt <= start_dt:
        return jsonify({"error": "end_ts must be after start_ts"}), 400

    # Generate new event_id
    event_id = str(uuid.uuid4())

    # Insert into DB
    db = get_db()
    try:
        db.execute("""
            INSERT INTO events (event_id, college_id, title, description, event_type, start_ts, end_ts, location, capacity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            j["college_id"],
            j["title"],
            j.get("description", ""),
            j["event_type"],
            j["start_ts"],
            j["end_ts"],
            j["location"],
            capacity,
            j.get("status", "published")
        ))
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": "Database integrity error", "details": str(e)}), 400

    return jsonify({"event_id": event_id, "message": "Event created successfully"}), 201

# List all available events
@app.route('/api/events/available', methods=['GET'])
def available_events():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM events")
    events = [dict(r) for r in cur.fetchall()]
    db.close()
    return jsonify(events)

# Mark attendance
@app.route('/api/events/<event_id>/attendance', methods=['POST'])
def mark_attendance(event_id):
    j = request.json
    student_uuid = j['student_uuid']
    method = j.get('method','manual')
    db = get_db()
    cur = db.cursor()
    att_id = str(uuid.uuid4())
    cur.execute("INSERT INTO attendance (attendance_id, event_id, student_uuid, checkin_at, method) VALUES (?, ?, ?, ?, ?)",
                (att_id, event_id, student_uuid, now_iso(), method))
    db.commit()
    return jsonify({"attendance_id": att_id}), 201

# Submit or update feedback
@app.route('/api/events/<event_id>/feedback', methods=['POST'])
def feedback(event_id):
    j = request.json
    student_uuid = j['student_uuid']
    rating = j.get('rating')
    comments = j.get('comments')
    fb_id = str(uuid.uuid4())
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("INSERT INTO feedback (feedback_id, event_id, student_uuid, rating, comments, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (fb_id, event_id, student_uuid, rating, comments, now_iso()))
        db.commit()
        return jsonify({"feedback_id": fb_id}), 201
    except sqlite3.IntegrityError:
        cur.execute("UPDATE feedback SET rating=?, comments=?, submitted_at=? WHERE event_id=? AND student_uuid=?",
                    (rating, comments, now_iso(), event_id, student_uuid))
        db.commit()
        return jsonify({"status":"updated"}), 200

# Event popularity report
@app.route('/api/reports/event_popularity', methods=['GET'])
def event_popularity():
    college_id = request.args.get('college_id')
    limit = int(request.args.get('limit','50'))
    db = get_db()
    cur = db.cursor()
    q = """
    SELECT e.event_id, e.title, e.event_type, e.start_ts,
      COUNT(r.registration_id) as registrations
    FROM events e
    LEFT JOIN registrations r ON r.event_id = e.event_id
    WHERE (? IS NULL OR e.college_id = ?)
    GROUP BY e.event_id
    ORDER BY registrations DESC
    LIMIT ?
    """
    cur.execute(q, (college_id, college_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

# Event stats
@app.route('/api/reports/event_stats/<event_id>', methods=['GET'])
def event_stats(event_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) as regs FROM registrations WHERE event_id=?", (event_id,))
    row = cur.fetchone()
    regs = row['regs'] if row else 0
    cur.execute("SELECT COUNT(DISTINCT student_uuid) as attended FROM attendance WHERE event_id=?", (event_id,))
    attended = cur.fetchone()['attended']
    cur.execute("SELECT AVG(rating) as avg_rating FROM feedback WHERE event_id=?", (event_id,))
    avg_rating = cur.fetchone()['avg_rating']
    attendance_pct = (attended / regs * 100) if regs and regs>0 else None
    return jsonify({"event_id": event_id, "registrations": regs, "attended": attended, "attendance_pct": attendance_pct, "avg_rating": avg_rating})

# Student participation
@app.route('/api/reports/student_participation', methods=['GET'])
def student_participation():
    student_uuid = request.args.get('student_uuid')
    college_id = request.args.get('college_id')
    db = get_db()
    cur = db.cursor()
    q = """
    SELECT COUNT(DISTINCT a.event_id) as attended_events
    FROM attendance a
    JOIN events e on e.event_id = a.event_id
    WHERE a.student_uuid = ? AND (? IS NULL OR e.college_id = ?)
    """
    cur.execute(q, (student_uuid, college_id, college_id))
    row = cur.fetchone()
    return jsonify({"student_uuid": student_uuid, "attended_events": row['attended_events'] if row else 0})

# Top active students
@app.route('/api/reports/top_active_students', methods=['GET'])
def top_active_students():
    college_id = request.args.get('college_id')
    limit = int(request.args.get('limit','3'))
    db = get_db()
    cur = db.cursor()
    q = """
    SELECT s.student_uuid, s.name, COUNT(DISTINCT a.event_id) as events_attended
    FROM students s
    JOIN attendance a ON a.student_uuid = s.student_uuid
    JOIN events e ON e.event_id = a.event_id
    WHERE (? IS NULL OR s.college_id = ?)
    GROUP BY s.student_uuid
    ORDER BY events_attended DESC
    LIMIT ?
    """
    cur.execute(q, (college_id, college_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

if __name__ == '__main__':
    with app.app_context():
        init_db()
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT OR IGNORE INTO colleges (college_id, name, timezone) VALUES (?, ?, ?)",
                ("college-1", "Sample College", "Asia/Kolkata"))
        db.commit()
    app.run(debug=True)
