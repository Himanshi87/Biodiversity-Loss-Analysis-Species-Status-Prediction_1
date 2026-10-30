"""BioRisk web server: login with email notifications + protected predictor.
Run:  pip install -r requirements-web.txt   then   python server.py   ->  http://127.0.0.1:5000
SMTP settings come from environment variables (see README). Without them, emails are printed in this console (development mode)."""
import os, re, secrets, smtplib, sqlite3, ssl, time
from email.message import EmailMessage
from pathlib import Path
from flask import Flask, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).parent
DB_PATH = BASE / "users.db"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PUBLIC = {"style.css", "script.js", "auth.js"}
FAILS = {}


def _secret():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    f = BASE / ".secret_key"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
    return f.read_text().strip()


app = Flask(__name__, static_folder=None)
app.secret_key = _secret()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("HTTPS") == "1", PERMANENT_SESSION_LIFETIME=7 * 86400)


def q(sql, args=(), one=False):
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.fetchone() if one else cur.fetchall()
    finally:
        c.close()


q("CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY, name TEXT, pw TEXT, verified INTEGER DEFAULT 1)")


def smtp_ready():
    return bool(os.environ.get("SMTP_HOST"))


def send_mail(to, subject, body):
    if not smtp_ready():
        print(f"\n[DEV MAIL - SMTP not configured]\nTo: {to}\nSubject: {subject}\n\n{body}\n")
        return True
    user = os.environ.get("SMTP_USER", "")
    msg = EmailMessage()
    msg["To"], msg["Subject"], msg["From"] = to, subject, os.environ.get("SMTP_FROM") or user
    msg.set_content(body)
    host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            s = smtplib.SMTP_SSL(host, port, timeout=20, context=ctx)
        else:
            s = smtplib.SMTP(host, port, timeout=20)
            s.starttls(context=ctx)
        with s:
            if user:
                s.login(user, os.environ.get("SMTP_PASS", ""))
            s.send_message(msg)
        return True
    except Exception as e:
        print("Mail error:", e)
        return False


def err(msg, status=400, **kw):
    return jsonify(error=msg, **kw), status


def body():
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


def clean_email(v):
    v = str(v or "").strip().lower()
    return v if len(v) <= 254 and EMAIL_RE.match(v) else None


def current():
    e = session.get("email")
    return q("SELECT email, name FROM users WHERE email=? AND verified=1", (e,), one=True) if e else None


@app.post("/api/register")
def register():
    d = body()
    email, name, pw = clean_email(d.get("email")), str(d.get("name", "")).strip()[:80], str(d.get("password", ""))
    if not name or not email:
        return err("Enter your name and a valid email address.")
    if len(pw) < 8:
        return err("Password must be at least 8 characters.")
    if q("SELECT 1 FROM users WHERE email=?", (email,), one=True):
        return err("This email is already registered. Please log in.", 409)
    q("INSERT INTO users(email, name, pw, verified) VALUES(?,?,?,1)", (email, name, generate_password_hash(pw)))
    session.clear()
    session.permanent = True
    session["email"] = email
    send_mail(email, "Welcome to BioRisk",
              f"Hi {name},\n\nYour BioRisk account has been created with this email address ({email}).\nYou can now log in and use the predictor.\n")
    return jsonify(ok=True, dev=not smtp_ready())


def locked(k):
    n, t = FAILS.get(k, (0, 0))
    if n >= 5 and time.time() - t >= 60:
        FAILS.pop(k, None)
        return False
    return n >= 5


@app.post("/api/login")
def login():
    d = body()
    email, pw = clean_email(d.get("email")), str(d.get("password", ""))
    if not email:
        return err("Invalid email or password.", 401)
    if locked(email):
        return err("Too many failed attempts. Try again in a minute.", 429)
    u = q("SELECT * FROM users WHERE email=?", (email,), one=True)
    if not u or not check_password_hash(u["pw"], pw):
        FAILS[email] = (FAILS.get(email, (0, 0))[0] + 1, time.time())
        return err("Invalid email or password.", 401)
    FAILS.pop(email, None)
    session.clear()
    session.permanent = True
    session["email"] = email
    when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    send_mail(email, "New login to your BioRisk account",
              f"Hi {u['name']},\n\nYour BioRisk account was logged in on {when}.\nIf this was not you, please contact the site administrator.\n")
    return jsonify(ok=True, dev=not smtp_ready())


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
def me():
    u = current()
    return jsonify(name=u["name"], email=u["email"]) if u else err("Not logged in.", 401)


@app.post("/api/email-report")
def email_report():
    u = current()
    if not u:
        return err("Please log in.", 401)
    text = str(body().get("text", ""))[:5000]
    if not text.strip():
        return err("Nothing to send.")
    if time.time() - session.get("rep", 0) < 10:
        return err("Please wait a few seconds before sending another report.", 429)
    session["rep"] = time.time()
    ok = send_mail(u["email"], "Your BioRisk prediction report",
                   f"Hi {u['name']},\n\n{text}\n\nBioRisk results are informational only and are not an official IUCN assessment.")
    return jsonify(ok=True, dev=not smtp_ready()) if ok else err("Could not send the email.", 502)


@app.get("/")
def home():
    return send_from_directory(BASE, "index.html") if current() else redirect("/login")


@app.get("/login")
def login_page():
    return redirect("/") if current() else send_from_directory(BASE, "login.html")


@app.get("/signup")
def signup_page():
    return redirect("/") if current() else send_from_directory(BASE, "signup.html")


@app.get("/data.js")
def data_js():
    return send_from_directory(BASE, "data.js") if current() else err("Please log in.", 401)


@app.get("/<path:name>")
def public(name):
    return send_from_directory(BASE, name) if name in PUBLIC else err("Not found.", 404)


@app.after_request
def headers(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    if request.path in ("/", "/data.js", "/login", "/signup") or request.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
