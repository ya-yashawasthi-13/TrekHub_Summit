
import os
import re
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

import google.generativeai as genai

# ---------- Setup ----------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

DB_PATH = ROOT_DIR / "trekhub.db"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("trekhub")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

GEMINI_MODEL = "gemini-2.5-flash"

frontend_dir = str((ROOT_DIR / "../frontend").resolve())
flask_app = Flask(__name__, static_folder=frontend_dir, static_url_path="/")
CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

@flask_app.route("/")
def index():
    return flask_app.send_static_file("index.html")


# ---------- SQLite helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
    return g.db


@flask_app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS treks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            region TEXT,
            difficulty TEXT NOT NULL,
            duration_days INTEGER NOT NULL,
            distance_km REAL,
            cost_inr INTEGER NOT NULL,
            best_time TEXT,
            max_altitude_ft INTEGER,
            description TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            question_text TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    c.execute("SELECT COUNT(*) FROM treks")
    if c.fetchone()[0] == 0:
        seed = [
            ("Hampta Pass", "Himachal Pradesh", "Himalayas", "Moderate", 5, 26.0, 10500,
             "June-September", 14100,
             "Crossover trek from lush Kullu valley to arid Lahaul's moonscape. Great first Himalayan trek."),
            ("Kedarkantha", "Uttarakhand", "Himalayas", "Easy", 6, 20.0, 8500,
             "December-April", 12500,
             "Popular winter snow trek with panoramic Himalayan views and pine forests."),
            ("Goechala", "Sikkim", "Himalayas", "Difficult", 10, 90.0, 22000,
             "April-May, October-November", 16000,
             "Tough high-altitude trek with close-up views of Mt Kanchenjunga."),
            ("Valley of Flowers", "Uttarakhand", "Himalayas", "Easy", 6, 38.0, 9500,
             "July-September", 14400,
             "UNESCO World Heritage site famous for its alpine flower meadows."),
            ("Dudhsagar Falls", "Goa", "Western Ghats", "Easy", 2, 14.0, 3500,
             "October-February", 2000,
             "Short trek to India's 5th tallest waterfall through Goa-Karnataka jungles."),
            ("Rajmachi Fort", "Maharashtra", "Western Ghats", "Easy", 2, 15.0, 2500,
             "June-February", 2700,
             "Weekend trek near Lonavala with monsoon waterfalls and twin forts."),
        ]
        c.executemany("""
            INSERT INTO treks (name, state, region, difficulty, duration_days, distance_km,
                               cost_inr, best_time, max_altitude_ft, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(*row, datetime.now(timezone.utc).isoformat()) for row in seed])
    conn.commit()
    conn.close()


init_db()


def row_to_dict(row):
    return {k: row[k] for k in row.keys()}


# ---------- API ----------
@flask_app.get("/api/")
def root():
    return jsonify({"app": "TrekHub SummitAI", "status": "ok"})


@flask_app.get("/api/treks")
def list_treks():
    state = request.args.get("state")
    difficulty = request.args.get("difficulty")
    max_budget = request.args.get("max_budget", type=int)
    max_days = request.args.get("max_days", type=int)
    q = request.args.get("q")

    sql = "SELECT * FROM treks WHERE 1=1"
    params = []
    if state:
        sql += " AND LOWER(state)=LOWER(?)"; params.append(state)
    if difficulty:
        sql += " AND LOWER(difficulty)=LOWER(?)"; params.append(difficulty)
    if max_budget is not None:
        sql += " AND cost_inr <= ?"; params.append(max_budget)
    if max_days is not None:
        sql += " AND duration_days <= ?"; params.append(max_days)
    if q:
        like = f"%{q.lower()}%"
        sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)"
        params.extend([like, like])
    sql += " ORDER BY name ASC"

    rows = get_db().execute(sql, params).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@flask_app.get("/api/treks/<int:trek_id>")
def get_trek(trek_id: int):
    row = get_db().execute("SELECT * FROM treks WHERE id=?", (trek_id,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(row_to_dict(row))


@flask_app.post("/api/treks")
def add_trek():
    data = request.get_json(force=True, silent=True) or {}
    required = ["name", "state", "difficulty", "duration_days", "cost_inr"]
    for k in required:
        if data.get(k) in (None, ""):
            return jsonify({"error": f"missing field: {k}"}), 400
    db = get_db()
    cur = db.execute("""
        INSERT INTO treks (name, state, region, difficulty, duration_days, distance_km,
                           cost_inr, best_time, max_altitude_ft, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"].strip(),
        data["state"].strip(),
        (data.get("region") or "").strip() or None,
        data["difficulty"].strip(),
        int(data["duration_days"]),
        float(data["distance_km"]) if data.get("distance_km") not in (None, "") else None,
        int(data["cost_inr"]),
        (data.get("best_time") or "").strip() or None,
        int(data["max_altitude_ft"]) if data.get("max_altitude_ft") not in (None, "") else None,
        (data.get("description") or "").strip() or None,
        datetime.now(timezone.utc).isoformat(),
    ))
    db.commit()
    row = db.execute("SELECT * FROM treks WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@flask_app.get("/api/states")
def list_states():
    rows = get_db().execute("SELECT DISTINCT state FROM treks ORDER BY state").fetchall()
    return jsonify([r["state"] for r in rows])


# ---------- Authentication ----------
@flask_app.post("/api/signup")
def signup():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    
    if not name or not email or not password:
        return jsonify({"error": "name, email, and password are required"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400
    
    db = get_db()
    try:
        password_hash = generate_password_hash(password)
        db.execute("""
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
        """, (name, email, password_hash, datetime.now(timezone.utc).isoformat()))
        db.commit()
        return jsonify({
            "message": "signup successful",
            "user": {"name": name, "email": email}
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "email already registered"}), 400


@flask_app.post("/api/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid email or password"}), 401
    
    return jsonify({
        "message": "login successful",
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]}
    }), 200


# ---------- Recommendation (scoring algorithm) ----------
@flask_app.post("/api/recommend")
def recommend():
    data = request.get_json(force=True, silent=True) or {}
    state = (data.get("state") or "").strip().lower()
    budget = data.get("budget")
    difficulty = (data.get("difficulty") or "").strip().lower()
    days = data.get("days")

    rows = get_db().execute("SELECT * FROM treks").fetchall()
    scored = []
    for r in rows:
        score = 0; reasons = []
        if state and r["state"].lower() == state:
            score += 40; reasons.append("State match +40")
        if budget is not None:
            try:
                if int(r["cost_inr"]) <= int(budget):
                    score += 30; reasons.append("Within budget +30")
            except (TypeError, ValueError): pass
        if difficulty and r["difficulty"].lower() == difficulty:
            score += 20; reasons.append("Difficulty match +20")
        if days is not None:
            try:
                if int(r["duration_days"]) <= int(days):
                    score += 10; reasons.append("Fits duration +10")
            except (TypeError, ValueError): pass
        if score > 0:
            item = row_to_dict(r)
            item["match_score"] = score
            item["match_reasons"] = reasons
            scored.append(item)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify(scored[:3])


# ---------- NLP search ----------
def _regex_fallback_extract(text: str):
    text_l = text.lower()
    budget = None
    m = re.search(r"(?:under|below|less than|upto|up to|within)?\s*(?:rs\.?|inr|₹)?\s*(\d{3,6})", text_l)
    if m: budget = int(m.group(1))
    difficulty = None
    for lvl in ["easy", "moderate", "difficult", "hard"]:
        if lvl in text_l:
            difficulty = "Difficult" if lvl == "hard" else lvl.capitalize(); break
    STATES = ["Himachal Pradesh", "Uttarakhand", "Jammu and Kashmir", "Ladakh", "Sikkim",
              "Arunachal Pradesh", "Meghalaya", "Nagaland", "Mizoram", "Manipur",
              "Kerala", "Karnataka", "Tamil Nadu", "Maharashtra", "Goa", "Rajasthan",
              "Madhya Pradesh", "West Bengal", "Assam", "Gujarat"]
    state = next((s for s in STATES if s.lower() in text_l), None)
    days = None
    m = re.search(r"(\d{1,2})\s*(?:day|days|d)\b", text_l)
    if m: days = int(m.group(1))
    return {"budget": budget, "state": state, "difficulty": difficulty, "days": days}


@flask_app.post("/api/search/nlp")
def nlp_search():
    data = request.get_json(force=True, silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    filters = {"budget": None, "state": None, "difficulty": None, "days": None}
    used_ai = False

    if GOOGLE_API_KEY:
        try:
            prompt = f"""Extract trek search filters from this user query. Return ONLY strict JSON.
Query: "{query}"

Schema:
{{
  "state": "<Indian state name or null>",
  "difficulty": "<Easy|Moderate|Difficult or null>",
  "budget": <max cost in INR as integer or null>,
  "days": <max trip duration in days as integer or null>
}}"""
            model = genai.GenerativeModel(GEMINI_MODEL)
            resp = model.generate_content(prompt)
            raw = (resp.text or "").strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
            parsed = json.loads(raw)
            for k in filters:
                if parsed.get(k) not in (None, "", "null"):
                    filters[k] = parsed.get(k)
            used_ai = True
        except Exception as e:
            logger.warning(f"Gemini NLP parse failed, using regex fallback: {e}")

    if not used_ai:
        filters.update(_regex_fallback_extract(query))

    rows = get_db().execute("SELECT * FROM treks").fetchall()
    results = []
    for r in rows:
        ok = True
        if filters["state"] and r["state"].lower() != str(filters["state"]).lower(): ok = False
        if filters["difficulty"] and r["difficulty"].lower() != str(filters["difficulty"]).lower(): ok = False
        if filters["budget"] is not None and r["cost_inr"] > int(filters["budget"]): ok = False
        if filters["days"] is not None and r["duration_days"] > int(filters["days"]): ok = False
        if ok: results.append(row_to_dict(r))

    return jsonify({"filters": filters, "used_ai": used_ai, "results": results[:10]})


# ---------- Chatbot ----------
@flask_app.post("/api/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "default").strip()
    if not message:
        return jsonify({"error": "message required"}), 400

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute("INSERT INTO chat_history(session_id, role, content, created_at) VALUES (?,?,?,?)",
               (session_id, "user", message, now))
    db.commit()

    if not GOOGLE_API_KEY:
        reply = "Chatbot is not configured. Please add GOOGLE_API_KEY."
    else:
        try:
            hist_rows = db.execute(
                "SELECT role, content FROM chat_history WHERE session_id=? ORDER BY id DESC LIMIT 10",
                (session_id,)).fetchall()
            hist = list(reversed([row_to_dict(r) for r in hist_rows]))
            treks = db.execute("SELECT name, state, difficulty, duration_days, cost_inr, best_time FROM treks").fetchall()
            trek_list = "\n".join(
                f"- {t['name']} ({t['state']}, {t['difficulty']}, {t['duration_days']} days, ₹{t['cost_inr']}, best: {t['best_time']})"
                for t in treks)
            system_msg = ("You are TrekHub SummitAI — a friendly expert on Indian trekking. "
                          "Answer briefly (3-5 sentences). Suggest treks, seasons, gear, fitness tips. "
                          "Prefer treks from this catalogue when relevant:\n" + trek_list)
            convo = system_msg + "\n\n"
            for h in hist[:-1]:
                convo += f"{h['role'].capitalize()}: {h['content']}\n"
            convo += f"User: {message}\nAssistant:"
            model = genai.GenerativeModel(GEMINI_MODEL)
            resp = model.generate_content(convo)
            reply = (resp.text or "").strip() or "Sorry, I couldn't generate a reply."
        except Exception as e:
            logger.exception("Gemini chat failed")
            reply = f"AI error: {e}"

    db.execute("INSERT INTO chat_history(session_id, role, content, created_at) VALUES (?,?,?,?)",
               (session_id, "assistant", reply, datetime.now(timezone.utc).isoformat()))
    db.commit()
    return jsonify({"reply": reply, "session_id": session_id})


@flask_app.get("/api/chat/history")
def chat_history():
    session_id = request.args.get("session_id", "default")
    rows = get_db().execute(
        "SELECT role, content, created_at FROM chat_history WHERE session_id=? ORDER BY id ASC",
        (session_id,)).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


# ---------- FAQ / Q&A ----------
@flask_app.get("/api/faq")
def get_faqs():
    db = get_db()
    questions = db.execute("SELECT * FROM questions ORDER BY created_at DESC").fetchall()
    answers = db.execute("SELECT * FROM answers ORDER BY created_at ASC").fetchall()
    
    q_list = []
    for q in questions:
        q_dict = row_to_dict(q)
        q_dict["answers"] = [row_to_dict(a) for a in answers if a["question_id"] == q["id"]]
        q_list.append(q_dict)
        
    return jsonify(q_list)

@flask_app.post("/api/faq/question")
def add_question():
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("user_id")
    user_name = data.get("user_name")
    question_text = (data.get("question_text") or "").strip()
    
    if not user_id or not user_name or not question_text:
        return jsonify({"error": "missing required fields"}), 400
        
    db = get_db()
    db.execute(
        "INSERT INTO questions (user_id, user_name, question_text, created_at) VALUES (?, ?, ?, ?)",
        (user_id, user_name, question_text, datetime.now(timezone.utc).isoformat())
    )
    db.commit()
    return jsonify({"message": "Question posted successfully"}), 201

@flask_app.post("/api/faq/answer")
def add_answer():
    data = request.get_json(force=True, silent=True) or {}
    question_id = data.get("question_id")
    user_id = data.get("user_id")
    user_name = data.get("user_name")
    answer_text = (data.get("answer_text") or "").strip()
    
    if not question_id or not user_id or not user_name or not answer_text:
        return jsonify({"error": "missing required fields"}), 400
        
    db = get_db()
    db.execute(
        "INSERT INTO answers (question_id, user_id, user_name, answer_text, created_at) VALUES (?, ?, ?, ?, ?)",
        (question_id, user_id, user_name, answer_text, datetime.now(timezone.utc).isoformat())
    )
    db.commit()
    return jsonify({"message": "Answer posted successfully"}), 201

@flask_app.delete("/api/faq/question/<int:question_id>")
def delete_question(question_id):
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("user_id")
    
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400
        
    db = get_db()
    question = db.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    if not question:
        return jsonify({"error": "Question not found"}), 404
        
    if question["user_id"] != user_id:
        return jsonify({"error": "Unauthorized"}), 403
        
    db.execute("DELETE FROM answers WHERE question_id = ?", (question_id,))
    db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    db.commit()
    
    return jsonify({"message": "Question deleted successfully"}), 200

@flask_app.delete("/api/faq/answer/<int:answer_id>")
def delete_answer(answer_id):
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("user_id")
    
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400
        
    db = get_db()
    answer = db.execute("SELECT * FROM answers WHERE id = ?", (answer_id,)).fetchone()
    if not answer:
        return jsonify({"error": "Answer not found"}), 404
        
    if answer["user_id"] != user_id:
        return jsonify({"error": "Unauthorized"}), 403
        
    db.execute("DELETE FROM answers WHERE id = ?", (answer_id,))
    db.commit()
    
    return jsonify({"message": "Answer deleted successfully"}), 200


# ASGI wrapper (only needed if you run under uvicorn). For normal `flask run`, ignore.
try:
    from asgiref.wsgi import WsgiToAsgi
    app = WsgiToAsgi(flask_app)
except ImportError:
    pass


if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=8001, debug=True)