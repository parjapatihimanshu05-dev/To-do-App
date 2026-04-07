from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE ----------
DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Fixed: added parentheses
    return conn

def init_db():
    db = get_db()
    
    # USERS TABLE
    db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # TASKS TABLE
    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task TEXT,
            category TEXT,
            priority TEXT,
            done INTEGER DEFAULT 0
        )
    """)

    # Add missing columns safely
    existing_columns = [col[1] for col in db.execute("PRAGMA table_info(tasks)").fetchall()]
    for col in ["start_date", "end_date", "day", "created_at"]:
        if col not in existing_columns:
            db.execute(f"ALTER TABLE tasks ADD COLUMN {col} TEXT")

    db.commit()
    db.close()

init_db()

# ---------- AUTH ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        db = get_db()
        result = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (user, pwd)
        ).fetchone()
        db.close()

        if result:
            session['user'] = result['id']  # Fixed: access column by name
            return redirect('/dashboard')
        return "Invalid login"

    return render_template('login.html')


@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (user, pwd)
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.close()
            return "Username already exists"
        db.close()
        return redirect('/')

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    db = get_db()
    tasks = db.execute(
        "SELECT * FROM tasks WHERE user_id=?",
        (session['user'],)
    ).fetchall()
    db.close()

    completed = sum(1 for t in tasks if t["done"] == 1)
    total = len(tasks)
    progress = int((completed / total) * 100) if total else 0

    return render_template('index.html', tasks=tasks, progress=progress)


# ---------- ADD TASK ----------
@app.route('/add', methods=['POST'])
def add():
    start = request.form['start_date']
    end = request.form['end_date']

    try:
        day = datetime.strptime(start, "%Y-%m-%d").strftime("%A")
    except ValueError:
        try:
            day = datetime.strptime(start, "%d/%m/%Y").strftime("%A")
        except ValueError:
            day = ""

    db = get_db()
    db.execute("""INSERT INTO tasks
        (user_id, task, category, priority, done, created_at, start_date, end_date, day)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session['user'],
            request.form['task'],
            request.form['category'],
            request.form['priority'],
            0,
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            start,
            end,
            day
        )
    )
    db.commit()
    db.close()
    return redirect('/dashboard')


# ---------- DONE ----------
@app.route('/done/<int:id>')
def done(id):
    db = get_db()
    task = db.execute("SELECT done FROM tasks WHERE id=?", (id,)).fetchone()
    if task:
        new_status = 0 if task["done"] == 1 else 1
        db.execute("UPDATE tasks SET done=? WHERE id=?", (new_status, id))
        db.commit()
    db.close()
    return redirect('/dashboard')


# ---------- DELETE ----------
@app.route('/delete/<int:id>')
def delete(id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect('/dashboard')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
