from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime, timedelta
import sqlite3, os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "tracker.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret-key")

STATUSES = ["Interested", "Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            course TEXT DEFAULT '', graduation_year INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS internships (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            company TEXT NOT NULL, role TEXT NOT NULL, location TEXT DEFAULT 'Not specified',
            work_mode TEXT DEFAULT 'Hybrid', stipend TEXT DEFAULT '', source_url TEXT DEFAULT '',
            description TEXT DEFAULT '', skills TEXT DEFAULT '', deadline TEXT,
            status TEXT DEFAULT 'Interested', priority TEXT DEFAULT 'Medium',
            notes TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            title TEXT NOT NULL, category TEXT DEFAULT 'General', done INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        # Sample internships are inserted per account at registration, not globally.

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def seed_checklist(user_id):
    items = [
        ("Update master resume", "Documents"), ("Prepare a tailored resume", "Documents"),
        ("Update LinkedIn profile", "Profile"), ("Prepare project portfolio", "Profile"),
        ("Collect academic transcript", "Documents"), ("Practice common interview questions", "Preparation")
    ]
    with db() as con:
        con.executemany("INSERT INTO checklist(user_id,title,category) VALUES(?,?,?)",
                        [(user_id, title, cat) for title, cat in items])

@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        course = request.form.get("course","").strip()
        grad = request.form.get("graduation_year") or None
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password with at least 8 characters.", "danger")
            return render_template("auth.html", mode="register")
        try:
            with db() as con:
                cur = con.execute("INSERT INTO users(name,email,password_hash,course,graduation_year) VALUES(?,?,?,?,?)",
                    (name,email,generate_password_hash(password),course,grad))
                uid = cur.lastrowid
            seed_checklist(uid)
            session["user_id"], session["user_name"] = uid, name
            flash("Your workspace is ready. Start adding opportunities!", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"], session["user_name"] = user["id"], user["name"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "danger")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    with db() as con:
        rows = con.execute("SELECT * FROM internships WHERE user_id=? ORDER BY CASE WHEN deadline IS NULL OR deadline='' THEN 1 ELSE 0 END, deadline ASC", (uid,)).fetchall()
        tasks = con.execute("SELECT * FROM checklist WHERE user_id=? ORDER BY done, id LIMIT 5", (uid,)).fetchall()
    today = date.today().isoformat()
    stats = {
        "total": len(rows),
        "active": sum(r["status"] in ("Applied","Assessment","Interview") for r in rows),
        "interviews": sum(r["status"] == "Interview" for r in rows),
        "offers": sum(r["status"] == "Offer" for r in rows),
        "upcoming": sum(bool(r["deadline"]) and today <= r["deadline"] <= (date.today()+timedelta(days=7)).isoformat() and r["status"] not in ("Rejected","Withdrawn","Offer") for r in rows)
    }
    upcoming = [r for r in rows if r["deadline"] and r["deadline"] >= today and r["status"] not in ("Rejected","Withdrawn","Offer")][:5]
    return render_template("dashboard.html", stats=stats, internships=rows[:5], upcoming=upcoming, tasks=tasks, today=today)

@app.route("/opportunities")
@login_required
def opportunities():
    q = request.args.get("q","").strip()
    status = request.args.get("status","")
    with db() as con:
        sql = "SELECT * FROM internships WHERE user_id=?"
        params = [session["user_id"]]
        if q:
            sql += " AND (company LIKE ? OR role LIKE ? OR skills LIKE ?)"
            params += [f"%{q}%"]*3
        if status:
            sql += " AND status=?"; params.append(status)
        sql += " ORDER BY created_at DESC"
        rows = con.execute(sql, params).fetchall()
    return render_template("opportunities.html", internships=rows, q=q, selected_status=status, statuses=STATUSES)

@app.route("/opportunities/new", methods=["GET","POST"])
@app.route("/opportunities/<int:item_id>/edit", methods=["GET","POST"])
@login_required
def opportunity_form(item_id=None):
    item = None
    if item_id:
        with db() as con:
            item = con.execute("SELECT * FROM internships WHERE id=? AND user_id=?", (item_id,session["user_id"])).fetchone()
        if not item:
            flash("Opportunity not found.", "danger"); return redirect(url_for("opportunities"))
    if request.method == "POST":
        fields = [request.form.get(k,"").strip() for k in ["company","role","location","work_mode","stipend","source_url","description","skills","deadline","status","priority","notes"]]
        if not fields[0] or not fields[1]:
            flash("Company and role are required.", "danger")
            return render_template("opportunity_form.html", item=request.form, statuses=STATUSES)
        if fields[10] not in ("Low","Medium","High"): fields[10] = "Medium"
        with db() as con:
            if item_id:
                con.execute("""UPDATE internships SET company=?,role=?,location=?,work_mode=?,stipend=?,source_url=?,description=?,skills=?,deadline=?,status=?,priority=?,notes=? WHERE id=? AND user_id=?""",
                            (*fields,item_id,session["user_id"]))
                flash("Opportunity updated.", "success")
            else:
                con.execute("""INSERT INTO internships(user_id,company,role,location,work_mode,stipend,source_url,description,skills,deadline,status,priority,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (session["user_id"],*fields))
                flash("Opportunity saved to your tracker.", "success")
        return redirect(url_for("opportunities"))
    return render_template("opportunity_form.html", item=item, statuses=STATUSES)

@app.route("/opportunities/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_opportunity(item_id):
    with db() as con:
        con.execute("DELETE FROM internships WHERE id=? AND user_id=?", (item_id,session["user_id"]))
    flash("Opportunity deleted.", "info")
    return redirect(url_for("opportunities"))

@app.route("/opportunities/<int:item_id>/status", methods=["POST"])
@login_required
def update_status(item_id):
    status = request.form.get("status","Interested")
    if status not in STATUSES: status = "Interested"
    with db() as con:
        con.execute("UPDATE internships SET status=? WHERE id=? AND user_id=?", (status,item_id,session["user_id"]))
    flash("Application status updated.", "success")
    return redirect(request.referrer or url_for("opportunities"))

@app.route("/checklist", methods=["GET","POST"])
@login_required
def checklist_page():
    uid = session["user_id"]
    if request.method == "POST":
        action = request.form.get("action")
        with db() as con:
            if action == "toggle":
                con.execute("UPDATE checklist SET done=CASE done WHEN 1 THEN 0 ELSE 1 END WHERE id=? AND user_id=?",
                            (request.form.get("item_id"),uid))
            elif action == "add":
                title=request.form.get("title","").strip()
                if title:
                    con.execute("INSERT INTO checklist(user_id,title,category) VALUES(?,?,?)",(uid,title,request.form.get("category","General")))
            elif action == "delete":
                con.execute("DELETE FROM checklist WHERE id=? AND user_id=?",(request.form.get("item_id"),uid))
        return redirect(url_for("checklist_page"))
    with db() as con:
        tasks = con.execute("SELECT * FROM checklist WHERE user_id=? ORDER BY category,done,id",(uid,)).fetchall()
    done = sum(t["done"] for t in tasks)
    return render_template("checklist.html", tasks=tasks, done=done, total=len(tasks))

@app.route("/reports")
@login_required
def reports():
    with db() as con:
        rows = con.execute("SELECT status, COUNT(*) AS count FROM internships WHERE user_id=? GROUP BY status",(session["user_id"],)).fetchall()
        items = con.execute("SELECT * FROM internships WHERE user_id=? ORDER BY created_at DESC",(session["user_id"],)).fetchall()
    counts = {s:0 for s in STATUSES}
    for row in rows: counts[row["status"]] = row["count"]
    total = len(items)
    applied = sum(counts[s] for s in ["Applied","Assessment","Interview","Offer","Rejected"])
    rate = round((counts["Offer"]/applied)*100) if applied else 0
    return render_template("reports.html", counts=counts, statuses=STATUSES, total=total, rate=rate, internships=items)

@app.route("/api/stats")
@login_required
def api_stats():
    with db() as con:
        rows = con.execute("SELECT status,COUNT(*) count FROM internships WHERE user_id=? GROUP BY status",(session["user_id"],)).fetchall()
    return jsonify({r["status"]:r["count"] for r in rows})

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    with db() as con:
        user = con.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
        if request.method == "POST":
            name=request.form.get("name","").strip()
            course=request.form.get("course","").strip()
            grad=request.form.get("graduation_year") or None
            if name:
                con.execute("UPDATE users SET name=?,course=?,graduation_year=? WHERE id=?",(name,course,grad,session["user_id"]))
                session["user_name"]=name
                flash("Profile updated.", "success")
                return redirect(url_for("profile"))
    return render_template("profile.html", user=user)

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

init_db()
if __name__ == "__main__":
    app.run(debug=True)
