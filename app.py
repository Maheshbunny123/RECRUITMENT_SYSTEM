from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from ml.resume_screening import ResumeScreener
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-2024'
app.config['UPLOAD_FOLDER'] = 'resumes'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}

screener = ResumeScreener()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
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

@app.route('/')
def index():
    return render_template('landing.html')

# ==================== AUTHENTICATION ====================

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
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            flash('Login successful!', 'success')
            
            if role == 'recruiter':
                return redirect(url_for('recruiter_dashboard'))
            else:
                return redirect(url_for('jobseeker_dashboard'))
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
            conn.execute(
                'INSERT INTO users (username, email, password, role, full_name, phone) VALUES (?, ?, ?, ?, ?, ?)',
                (username, email, generate_password_hash(password), role, full_name, phone)
            )
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

# ==================== RECRUITER ROUTES ====================

@app.route('/recruiter/dashboard')
def recruiter_dashboard():
    if 'user_id' not in session or session.get('role') != 'recruiter':
        flash('Access denied. Recruiters only.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    
    my_jobs = conn.execute('SELECT COUNT(*) as count FROM jobs WHERE posted_by = ?', (session['user_id'],)).fetchone()['count']
    total_applications = conn.execute('''
        SELECT COUNT(*) as count FROM applications a
        JOIN jobs j ON a.job_id = j.id WHERE j.posted_by = ?
    ''', (session['user_id'],)).fetchone()['count']
    pending = conn.execute('''
        SELECT COUNT(*) as count FROM applications a
        JOIN jobs j ON a.job_id = j.id WHERE j.posted_by = ? AND a.status = "pending"
    ''', (session['user_id'],)).fetchone()['count']
    shortlisted = conn.execute('''
        SELECT COUNT(*) as count FROM applications a
        JOIN jobs j ON a.job_id = j.id WHERE j.posted_by = ? AND a.status = "shortlisted"
    ''', (session['user_id'],)).fetchone()['count']
    
    jobs = conn.execute('''
        SELECT j.*, (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as application_count
        FROM jobs j WHERE j.posted_by = ? ORDER BY j.created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    recent_apps = conn.execute('''
        SELECT a.*, j.title as job_title, u.full_name as candidate_name, u.email as candidate_email
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.user_id = u.id
        WHERE j.posted_by = ?
        ORDER BY a.applied_at DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    stats = {'total_jobs': my_jobs, 'total_applications': total_applications, 
             'pending_applications': pending, 'shortlisted': shortlisted}
    
    return render_template('recruiter_dashboard.html', stats=stats, jobs=jobs, applications=recent_apps)

@app.route('/recruiter/jobs/create', methods=['GET', 'POST'])
def create_job():
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        conn = get_db()
        conn.execute('''
            INSERT INTO jobs (title, description, requirements, location, job_type, 
                            experience_level, salary_range, posted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (request.form.get('title'), request.form.get('description'), 
              request.form.get('requirements'), request.form.get('location'),
              request.form.get('job_type'), request.form.get('experience_level'),
              request.form.get('salary_range'), session['user_id']))
        conn.commit()
        conn.close()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('recruiter_dashboard'))
    
    return render_template('create_job.html')

@app.route('/recruiter/jobs/<int:job_id>/applications')
def view_applications(job_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('login'))
    
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ? AND posted_by = ?', 
                       (job_id, session['user_id'])).fetchone()
    
    if not job:
        flash('Job not found', 'error')
        conn.close()
        return redirect(url_for('recruiter_dashboard'))
    
    applications = conn.execute('''
        SELECT a.*, u.full_name as candidate_name, u.email as candidate_email, u.phone as candidate_phone
        FROM applications a
        JOIN users u ON a.user_id = u.id
        WHERE a.job_id = ?
        ORDER BY a.match_score DESC, a.applied_at DESC
    ''', (job_id,)).fetchall()
    conn.close()
    
    return render_template('recruiter_applications.html', job=job, applications=applications)

@app.route('/recruiter/applications/<int:app_id>/update', methods=['POST'])
def update_status(app_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    app = conn.execute('''
        SELECT a.*, j.posted_by FROM applications a
        JOIN jobs j ON a.job_id = j.id WHERE a.id = ?
    ''', (app_id,)).fetchone()
    
    if not app or app['posted_by'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn.execute('UPDATE applications SET status = ? WHERE id = ?', 
                 (request.json.get('status'), app_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/recruiter/applications/<int:app_id>/ai-shortlist', methods=['POST'])
def ai_shortlist(app_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    app = conn.execute('''
        SELECT a.*, j.posted_by, j.requirements, j.title FROM applications a
        JOIN jobs j ON a.job_id = j.id WHERE a.id = ?
    ''', (app_id,)).fetchone()
    
    if not app or app['posted_by'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    
    result = screener.screen_resume(app['resume_path'], app['requirements'], app['title'])
    status = 'shortlisted' if result['match_score'] >= 60 else 'rejected'
    
    conn.execute('UPDATE applications SET status = ?, screening_result = ? WHERE id = ?',
                 (status, json.dumps(result), app_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'status': status, 'match_score': result['match_score']})

@app.route('/recruiter/jobs/<int:job_id>/ai-shortlist-all', methods=['POST'])
def ai_shortlist_all(job_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()

    job = conn.execute(
        'SELECT * FROM jobs WHERE id = ? AND posted_by = ?',
        (job_id, session['user_id'])
    ).fetchone()

    if not job:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404

    applications = conn.execute(
        'SELECT * FROM applications WHERE job_id = ? AND status = "pending"',
        (job_id,)
    ).fetchall()

    updated = 0
    for app in applications:
        result = screener.screen_resume(
            app['resume_path'],
            job['requirements'],
            job['title']
        )
        status = 'shortlisted' if result['match_score'] >= 60 else 'rejected'

        conn.execute(
            'UPDATE applications SET status = ?, screening_result = ? WHERE id = ?',
            (status, json.dumps(result), app['id'])
        )
        updated += 1

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'processed': updated})

@app.route('/recruiter/applications/<int:app_id>/download-report')
def download_ai_report(app_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('login'))

    conn = get_db()
    app = conn.execute(
        'SELECT a.screening_result, j.posted_by FROM applications a JOIN jobs j ON a.job_id=j.id WHERE a.id=?',
        (app_id,)
    ).fetchone()
    conn.close()

    if not app or app['posted_by'] != session['user_id']:
        return redirect(url_for('recruiter_dashboard'))

    result = json.loads(app['screening_result'])

    file_path = f"ai_report_{app_id}.pdf"
    c = canvas.Canvas(file_path, pagesize=letter)
    c.drawString(50, 750, f"Match Score: {result['match_score']}%")
    c.drawString(50, 720, f"Recommendation: {result['recommendation']}")
    c.drawString(50, 690, f"Experience: {result['experience_years']} years")
    c.drawString(50, 660, f"Education: {result['education_level']}")
    c.drawString(50, 630, f"Skills Matched: {', '.join(result['skills_matched'])}")
    c.save()

    return send_file(file_path, as_attachment=True)



# ==================== JOB SEEKER ROUTES ====================

@app.route('/jobseeker/dashboard')
def jobseeker_dashboard():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        flash('Access denied. Job seekers only.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    
    my_apps = conn.execute('SELECT COUNT(*) as count FROM applications WHERE user_id = ?', 
                          (session['user_id'],)).fetchone()['count']
    pending = conn.execute('SELECT COUNT(*) as count FROM applications WHERE user_id = ? AND status = "pending"',
                          (session['user_id'],)).fetchone()['count']
    shortlisted = conn.execute('SELECT COUNT(*) as count FROM applications WHERE user_id = ? AND status = "shortlisted"',
                              (session['user_id'],)).fetchone()['count']
    
    jobs = conn.execute('SELECT * FROM jobs WHERE status = "active" ORDER BY created_at DESC').fetchall()
    
    my_applications = conn.execute('''
        SELECT a.*, j.title as job_title, j.location, j.job_type
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.user_id = ?
        ORDER BY a.applied_at DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    stats = {'total_applications': my_apps, 'pending': pending, 'shortlisted': shortlisted}
    return render_template('jobseeker_dashboard.html', stats=stats, jobs=jobs, applications=my_applications)

@app.route('/jobseeker/jobs/<int:job_id>/apply', methods=['GET', 'POST'])
def apply_job(job_id):
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('login'))
    
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    
    # Check if already applied
    existing = conn.execute('SELECT * FROM applications WHERE job_id = ? AND user_id = ?',
                           (job_id, session['user_id'])).fetchone()
    
    if existing:
        flash('You have already applied for this job', 'warning')
        conn.close()
        return redirect(url_for('jobseeker_dashboard'))
    
    if request.method == 'POST':
        file = request.files['resume']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{session['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            result = screener.screen_resume(filepath, job['requirements'], job['title'])
            
            conn.execute('''
                INSERT INTO applications (job_id, user_id, resume_path, cover_letter,
                                        match_score, skills_matched, experience_years,
                                        education_level, screening_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (job_id, session['user_id'], filepath, request.form.get('cover_letter'),
                  result['match_score'], json.dumps(result['skills_matched']),
                  result.get('experience_years', 0), result.get('education_level', 'Unknown'),
                  json.dumps(result)))
            conn.commit()
            conn.close()
            flash(f'Application submitted! Your match score: {result["match_score"]}%', 'success')
            return redirect(url_for('jobseeker_dashboard'))
    
    conn.close()
    return render_template('apply_job.html', job=job)

@app.route('/jobseeker/resume-scorer', methods=['GET', 'POST'])
def resume_scorer():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files.get('resume')
        if file and allowed_file(file.filename):
            filename = secure_filename(f"temp_{session['username']}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            result = screener.analyze_resume_quality(filepath)
            os.remove(filepath)  # Remove temp file
            
            return render_template('resume_scorer.html', result=result)
    
    return render_template('resume_scorer.html')

@app.route('/jobseeker/job-matcher', methods=['GET', 'POST'])
def job_matcher():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files.get('resume')
        job_desc = request.form.get('job_description')
        
        if file and allowed_file(file.filename):
            filename = secure_filename(f"temp_{session['username']}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            result = screener.screen_resume(filepath, job_desc, "Job Position")
            os.remove(filepath)
            
            return render_template('job_matcher.html', result=result, job_desc=job_desc)
    
    return render_template('job_matcher.html')

@app.route('/download-resume/<int:app_id>')
def download_resume(app_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('login'))
    
    conn = get_db()
    app = conn.execute('''
        SELECT a.resume_path, j.posted_by FROM applications a
        JOIN jobs j ON a.job_id = j.id WHERE a.id = ?
    ''', (app_id,)).fetchone()
    conn.close()
    
    if not app or app['posted_by'] != session['user_id']:
        flash('Unauthorized', 'error')
        return redirect(url_for('recruiter_dashboard'))
    
    return send_file(app['resume_path'], as_attachment=True)

os.makedirs('resumes', exist_ok=True)
init_db()

