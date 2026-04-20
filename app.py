from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'enviro_ledger_secret_2024'

DB_PATH = 'database.db'

# ─── DB INIT ───────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','staff','analyst')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        value REAL NOT NULL,
        category TEXT,
        notes TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_updated INTEGER DEFAULT 0,
        original_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Seed default users
    users = [
        ('admin', hash_pw('admin123'), 'admin'),
        ('staff1', hash_pw('staff123'), 'staff'),
        ('analyst1', hash_pw('analyst123'), 'analyst'),
    ]
    for u in users:
        try:
            c.execute('INSERT INTO users (username,password,role) VALUES (?,?,?)', u)
        except:
            pass

    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── DECORATORS ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def log_action(user_id, action, details=''):
    conn = get_db()
    conn.execute('INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)',
                 (user_id, action, details))
    conn.commit()
    conn.close()

def carbon_footprint(type_, value):
    rates = {'electricity': 0.82, 'fuel': 2.31, 'water': 0.001, 'waste': 0.5, 'emissions': 1.0}
    return round(value * rates.get(type_, 0), 4)

# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=? AND password=?',
                            (username, hash_pw(password))).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            log_action(user['id'], 'LOGIN', f"User {username} logged in")
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_action(session['user_id'], 'LOGOUT', f"User {session['username']} logged out")
    session.clear()
    return redirect(url_for('login'))

# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    # totals per type
    totals = {}
    for t in ['electricity', 'fuel', 'water', 'waste', 'emissions']:
        row = conn.execute("SELECT COALESCE(SUM(value),0) as total FROM ledger WHERE type=? AND is_updated=0", (t,)).fetchone()
        totals[t] = round(row['total'], 2)

    total_carbon = sum(carbon_footprint(t, v) for t, v in totals.items())

    # recent 5 entries
    recent = conn.execute('''SELECT l.*, u.username FROM ledger l
        JOIN users u ON l.user_id=u.id
        WHERE l.is_updated=0 ORDER BY l.timestamp DESC LIMIT 5''').fetchall()

    # monthly chart data (last 6 months)
    monthly = {}
    for t in ['electricity', 'fuel', 'water', 'waste', 'emissions']:
        rows = conn.execute('''SELECT strftime('%Y-%m', timestamp) as month, SUM(value) as total
            FROM ledger WHERE type=? AND is_updated=0
            GROUP BY month ORDER BY month DESC LIMIT 6''', (t,)).fetchall()
        monthly[t] = [{'month': r['month'], 'total': round(r['total'], 2)} for r in rows]

    conn.close()
    return render_template('dashboard.html', totals=totals, total_carbon=round(total_carbon, 2),
                           recent=recent, monthly=monthly)

# ─── DATA ENTRY ───────────────────────────────────────────────────────────────

def entry_page(type_, template, allowed_roles=('admin', 'staff')):
    def view():
        if session.get('role') not in allowed_roles:
            flash('Access denied.', 'error')
            return redirect(url_for('dashboard'))

        conn = get_db()
        if session['role'] == 'staff':
            entries = conn.execute('''SELECT l.*, u.username FROM ledger l
                JOIN users u ON l.user_id=u.id
                WHERE l.type=? AND l.user_id=? ORDER BY l.timestamp DESC''',
                (type_, session['user_id'])).fetchall()
        else:
            entries = conn.execute('''SELECT l.*, u.username FROM ledger l
                JOIN users u ON l.user_id=u.id
                WHERE l.type=? ORDER BY l.timestamp DESC''', (type_,)).fetchall()
        conn.close()
        return render_template(template, entries=entries, type=type_)
    view.__name__ = f'page_{type_}'
    return view

@app.route('/electricity', methods=['GET', 'POST'])
@login_required
def electricity():
    return handle_entry('electricity', 'electricity.html', unit='kWh')

@app.route('/fuel', methods=['GET', 'POST'])
@login_required
def fuel():
    return handle_entry('fuel', 'fuel.html', unit='Liters')

@app.route('/water', methods=['GET', 'POST'])
@login_required
def water():
    return handle_entry('water', 'water.html', unit='Liters')

@app.route('/waste', methods=['GET', 'POST'])
@login_required
def waste():
    return handle_entry('waste', 'waste.html', unit='kg', has_category=True)

@app.route('/emissions', methods=['GET', 'POST'])
@login_required
def emissions():
    return handle_entry('emissions', 'emissions.html', unit='CO₂ kg')

def handle_entry(type_, template, unit='', has_category=False):
    if session.get('role') not in ('admin', 'staff'):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        value = request.form.get('value', '')
        category = request.form.get('category', '')
        notes = request.form.get('notes', '')

        errors = []
        try:
            val = float(value)
            if val < 0:
                errors.append('Value cannot be negative.')
        except:
            errors.append('Value must be a number.')

        if not value:
            errors.append('Value is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
        else:
            conn = get_db()
            conn.execute('INSERT INTO ledger (user_id, type, value, category, notes) VALUES (?,?,?,?,?)',
                         (session['user_id'], type_, val, category, notes))
            conn.commit()
            log_action(session['user_id'], f'ADD_{type_.upper()}',
                       f"Added {val} {unit} {'[' + category + ']' if category else ''}")
            conn.close()
            flash(f'{type_.capitalize()} entry added successfully.', 'success')
            return redirect(url_for(type_))

    conn = get_db()
    if session['role'] == 'staff':
        entries = conn.execute('''SELECT l.*, u.username FROM ledger l
            JOIN users u ON l.user_id=u.id
            WHERE l.type=? AND l.user_id=? AND l.is_updated=0 ORDER BY l.timestamp DESC''',
            (type_, session['user_id'])).fetchall()
    else:
        entries = conn.execute('''SELECT l.*, u.username FROM ledger l
            JOIN users u ON l.user_id=u.id
            WHERE l.type=? AND l.is_updated=0 ORDER BY l.timestamp DESC''', (type_,)).fetchall()
    conn.close()
    return render_template(template, entries=entries, has_category=has_category, unit=unit)

# ─── REPORTS ──────────────────────────────────────────────────────────────────

@app.route('/reports')
@login_required
def reports():
    if session.get('role') not in ('admin', 'analyst'):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db()
    type_filter = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = '''SELECT l.*, u.username FROM ledger l
        JOIN users u ON l.user_id=u.id WHERE l.is_updated=0'''
    params = []

    if type_filter:
        query += ' AND l.type=?'
        params.append(type_filter)
    if date_from:
        query += ' AND DATE(l.timestamp) >= ?'
        params.append(date_from)
    if date_to:
        query += ' AND DATE(l.timestamp) <= ?'
        params.append(date_to)

    query += ' ORDER BY l.timestamp DESC'
    entries = conn.execute(query, params).fetchall()

    # summary stats
    summary = {}
    for t in ['electricity', 'fuel', 'water', 'waste', 'emissions']:
        row = conn.execute("SELECT COALESCE(SUM(value),0) as total, COUNT(*) as count FROM ledger WHERE type=? AND is_updated=0", (t,)).fetchone()
        summary[t] = {'total': round(row['total'], 2), 'count': row['count'],
                      'carbon': carbon_footprint(t, row['total'])}

    conn.close()
    return render_template('reports.html', entries=entries, summary=summary,
                           type_filter=type_filter, date_from=date_from, date_to=date_to)

# ─── AUDIT LOGS (admin only) ──────────────────────────────────────────────────

@app.route('/audit')
@login_required
@role_required('admin')
def audit():
    conn = get_db()
    logs = conn.execute('''SELECT a.*, u.username FROM audit_logs a
        JOIN users u ON a.user_id=u.id ORDER BY a.timestamp DESC LIMIT 200''').fetchall()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('audit.html', logs=logs, users=users)

# ─── USER MGMT (admin only) ───────────────────────────────────────────────────

@app.route('/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_users():
    conn = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            role = request.form.get('role', 'staff')
            if username and password:
                try:
                    conn.execute('INSERT INTO users (username,password,role) VALUES (?,?,?)',
                                 (username, hash_pw(password), role))
                    conn.commit()
                    log_action(session['user_id'], 'ADD_USER', f"Created user: {username} [{role}]")
                    flash(f'User {username} created.', 'success')
                except:
                    flash('Username already exists.', 'error')
            else:
                flash('Username and password required.', 'error')
        elif action == 'delete':
            uid = request.form.get('user_id')
            if str(uid) != str(session['user_id']):
                conn.execute('DELETE FROM users WHERE id=?', (uid,))
                conn.commit()
                flash('User deleted.', 'success')
            else:
                flash("Cannot delete yourself.", 'error')

    users = conn.execute('SELECT * FROM users ORDER BY role, username').fetchall()
    conn.close()
    return render_template('users.html', users=users)

# ─── API: chart data ──────────────────────────────────────────────────────────

@app.route('/api/chart-data')
@login_required
def chart_data():
    conn = get_db()
    types = ['electricity', 'fuel', 'water', 'waste', 'emissions']
    data = {}
    for t in types:
        rows = conn.execute('''SELECT strftime('%Y-%m', timestamp) as month, SUM(value) as total
            FROM ledger WHERE type=? AND is_updated=0
            GROUP BY month ORDER BY month ASC LIMIT 6''', (t,)).fetchall()
        data[t] = [{'month': r['month'], 'total': round(r['total'], 2)} for r in rows]
    conn.close()
    return jsonify(data)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
