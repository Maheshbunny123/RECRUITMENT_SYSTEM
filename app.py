from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import json

# ---- ML Resume Screener ----
try:
    from ml.resume_screening import ResumeScreener
    screener = ResumeScreener()
except ImportError:
    screener = None
    print("Warning: ResumeScreener not found. Resume analysis disabled.")

# ---- Flask Setup ----
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-2024'
app.config['UPLOAD_FOLDER'] = 'resumes'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---- Helpers ----
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Jobs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            requirements TEXT NOT NULL,
            location TEXT,
            job_type TEXT,
            experience_level TEXT,
            salary_range TEXT,
            posted_by INTEGER,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by) REFERENCES users (id)
        )
    ''')

    # Applications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            resume_path TEXT NOT NULL,
            cover_letter TEXT,
            match_score REAL,
            skills_matched TEXT,
            experience_years INTEGER,
            education_level TEXT,
            status TEXT DEFAULT 'pending',
            screening_result TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Insert demo users safely
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password, role, full_name) VALUES (?, ?, ?, ?, ?)",
            ('recruiter1', 'recruiter@company.com', generate_password_hash('recruiter123'), 'recruiter', 'Demo Recruiter')
        )
        cursor.execute(
            "INSERT INTO users (username, email, password, role, full_name) VALUES (?, ?, ?, ?, ?)",
            ('jobseeker1', 'jobseeker@email.com', generate_password_hash('jobseeker123'), 'jobseeker', 'Demo Job Seeker')
        )
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()

# ---- Routes ----

@app.route('/')
def index():
    return render_template('landing.html')

# ------------------- AUTH -------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND role = ?', (username, role)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session.update({
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'full_name': user['full_name']
            })
            flash('Login successful!', 'success')
            return redirect(url_for('recruiter_dashboard') if role=='recruiter' else url_for('jobseeker_dashboard'))
        else:
            flash('Invalid credentials or role', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        
        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO users (username, email, password, role, full_name, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, generate_password_hash(password), role, full_name, phone))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

# ------------------- RECRUITER -------------------

def recruiter_required(func):
    def wrapper(*args, **kwargs):
        if session.get('role') != 'recruiter':
            flash('Access denied. Recruiters only.', 'error')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/recruiter/dashboard')
@recruiter_required
def recruiter_dashboard():
    conn = get_db()
    
    my_jobs = conn.execute('SELECT COUNT(*) FROM jobs WHERE posted_by=?', (session['user_id'],)).fetchone()[0]
    total_applications = conn.execute('''
        SELECT COUNT(*) FROM applications a JOIN jobs j ON a.job_id=j.id WHERE j.posted_by=?
    ''', (session['user_id'],)).fetchone()[0]
    
    pending = conn.execute('''
        SELECT COUNT(*) FROM applications a JOIN jobs j ON a.job_id=j.id
        WHERE j.posted_by=? AND a.status="pending"
    ''', (session['user_id'],)).fetchone()[0]
    
    shortlisted = conn.execute('''
        SELECT COUNT(*) FROM applications a JOIN jobs j ON a.job_id=j.id
        WHERE j.posted_by=? AND a.status="shortlisted"
    ''', (session['user_id'],)).fetchone()[0]
    
    jobs = conn.execute('''
        SELECT j.*, (SELECT COUNT(*) FROM applications WHERE job_id=j.id) as application_count
        FROM jobs j WHERE posted_by=? ORDER BY created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    recent_apps = conn.execute('''
        SELECT a.*, j.title AS job_title, u.full_name AS candidate_name, u.email AS candidate_email
        FROM applications a
        JOIN jobs j ON a.job_id=j.id
        JOIN users u ON a.user_id=u.id
        WHERE j.posted_by=?
        ORDER BY a.applied_at DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    stats = {
        'total_jobs': my_jobs,
        'total_applications': total_applications,
        'pending_applications': pending,
        'shortlisted': shortlisted
    }
    
    return render_template('recruiter_dashboard.html', stats=stats, jobs=jobs, applications=recent_apps)

# ------------------- JOB SEEKER -------------------

def jobseeker_required(func):
    def wrapper(*args, **kwargs):
        if session.get('role') != 'jobseeker':
            flash('Access denied. Job seekers only.', 'error')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/jobseeker/dashboard')
@jobseeker_required
def jobseeker_dashboard():
    conn = get_db()
    
    total_apps = conn.execute('SELECT COUNT(*) FROM applications WHERE user_id=?', (session['user_id'],)).fetchone()[0]
    pending = conn.execute('SELECT COUNT(*) FROM applications WHERE user_id=? AND status="pending"', (session['user_id'],)).fetchone()[0]
    shortlisted = conn.execute('SELECT COUNT(*) FROM applications WHERE user_id=? AND status="shortlisted"', (session['user_id'],)).fetchone()[0]
    
    jobs = conn.execute('SELECT * FROM jobs WHERE status="active" ORDER BY created_at DESC').fetchall()
    
    my_apps = conn.execute('''
        SELECT a.*, j.title AS job_title, j.location, j.job_type
        FROM applications a
        JOIN jobs j ON a.job_id=j.id
        WHERE a.user_id=? ORDER BY a.applied_at DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    stats = {'total_applications': total_apps, 'pending': pending, 'shortlisted': shortlisted}
    
    return render_template('jobseeker_dashboard.html', stats=stats, jobs=jobs, applications=my_apps)

# ---- INIT & RUN ----
if __name__ == '__main__':
    import os
    init_db()
    port = int(os.environ.get('PORT', 5000))  # Render will provide PORT
    app.run(host='0.0.0.0', port=port)

