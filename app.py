from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from ml.resume_screening import ResumeScreener
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
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
            role TEXT DEFAULT 'recruiter',
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
            candidate_name TEXT NOT NULL,
            candidate_email TEXT NOT NULL,
            candidate_phone TEXT,
            resume_path TEXT NOT NULL,
            cover_letter TEXT,
            match_score REAL,
            skills_matched TEXT,
            experience_years INTEGER,
            education_level TEXT,
            status TEXT DEFAULT 'pending',
            screening_result TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
    ''')
    
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            ('admin', 'admin@recruitment.com', generate_password_hash('admin123'), 'admin')
        )
    except sqlite3.IntegrityError:
        pass
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    # Show public jobs page
    return redirect(url_for('public_jobs'))

@app.route('/jobs')
def public_jobs():
    """Public page showing all active jobs - anyone can view"""
    conn = get_db()
    jobs = conn.execute('''
        SELECT j.*, u.username as posted_by_name,
               (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as application_count
        FROM jobs j
        LEFT JOIN users u ON j.posted_by = u.id
        WHERE j.status = 'active'
        ORDER BY j.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('public_jobs.html', jobs=jobs)

@app.route('/jobs/<int:job_id>/apply', methods=['GET', 'POST'])
def apply_job(job_id):
    """Public application page - anyone can apply"""
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ? AND status = "active"', (job_id,)).fetchone()
    conn.close()
    
    if not job:
        flash('Job not found or no longer available', 'error')
        return redirect(url_for('public_jobs'))
    
    if request.method == 'POST':
        candidate_name = request.form.get('candidate_name')
        candidate_email = request.form.get('candidate_email')
        candidate_phone = request.form.get('candidate_phone')
        cover_letter = request.form.get('cover_letter')
        
        if 'resume' not in request.files:
            flash('No resume file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['resume']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{candidate_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # AI Resume Screening
            screening_result = screener.screen_resume(filepath, job['requirements'], job['title'])
            
            conn = get_db()
            conn.execute('''
                INSERT INTO applications (job_id, candidate_name, candidate_email, 
                                        candidate_phone, resume_path, cover_letter,
                                        match_score, skills_matched, experience_years,
                                        education_level, screening_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (job_id, candidate_name, candidate_email, candidate_phone, filepath,
                  cover_letter, screening_result['match_score'],
                  json.dumps(screening_result['skills_matched']),
                  screening_result.get('experience_years', 0),
                  screening_result.get('education_level', 'Unknown'),
                  json.dumps(screening_result)))
            conn.commit()
            conn.close()
            
            flash('Application submitted successfully! You will be contacted if shortlisted.', 'success')
            return redirect(url_for('application_success'))
        else:
            flash('Invalid file type. Only PDF, DOCX, and TXT files are allowed.', 'error')
    
    return render_template('apply_job.html', job=job)

@app.route('/application_success')
def application_success():
    return render_template('success.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, generate_password_hash(password))
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
        finally:
            conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('public_jobs'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    # Get jobs posted by this user
    my_jobs = conn.execute('SELECT COUNT(*) as count FROM jobs WHERE posted_by = ? AND status = "active"', (session['user_id'],)).fetchone()['count']
    
    # Get applications for user's jobs
    my_applications = conn.execute('''
        SELECT COUNT(*) as count FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.posted_by = ?
    ''', (session['user_id'],)).fetchone()['count']
    
    pending_applications = conn.execute('''
        SELECT COUNT(*) as count FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.posted_by = ? AND a.status = "pending"
    ''', (session['user_id'],)).fetchone()['count']
    
    shortlisted = conn.execute('''
        SELECT COUNT(*) as count FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.posted_by = ? AND a.status = "shortlisted"
    ''', (session['user_id'],)).fetchone()['count']
    
    # Get user's jobs
    jobs = conn.execute('''
        SELECT j.*, 
               (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as application_count
        FROM jobs j
        WHERE j.posted_by = ? AND j.status = 'active'
        ORDER BY j.created_at DESC
        LIMIT 10
    ''', (session['user_id'],)).fetchall()
    
    # Get recent applications for user's jobs
    applications = conn.execute('''
        SELECT a.*, j.title as job_title
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.posted_by = ?
        ORDER BY a.applied_at DESC
        LIMIT 10
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    stats = {
        'total_jobs': my_jobs,
        'total_applications': my_applications,
        'pending_applications': pending_applications,
        'shortlisted': shortlisted
    }
    
    return render_template('dashboard.html', stats=stats, jobs=jobs, applications=applications)

@app.route('/jobs/create', methods=['GET', 'POST'])
def create_job():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        requirements = request.form.get('requirements')
        location = request.form.get('location')
        job_type = request.form.get('job_type')
        experience_level = request.form.get('experience_level')
        salary_range = request.form.get('salary_range')
        
        conn = get_db()
        conn.execute('''
            INSERT INTO jobs (title, description, requirements, location, job_type, 
                            experience_level, salary_range, posted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, requirements, location, job_type, 
              experience_level, salary_range, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Job posted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_job.html')

@app.route('/my-jobs/<int:job_id>/applications')
def view_applications(job_id):
    """View applications - only visible to job poster"""
    if 'user_id' not in session:
        flash('Please login to view applications', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    
    # Check if user owns this job
    job = conn.execute('SELECT * FROM jobs WHERE id = ? AND posted_by = ?', 
                       (job_id, session['user_id'])).fetchone()
    
    if not job:
        conn.close()
        flash('You do not have permission to view these applications', 'error')
        return redirect(url_for('dashboard'))
    
    applications = conn.execute('''
        SELECT * FROM applications 
        WHERE job_id = ? 
        ORDER BY match_score DESC, applied_at DESC
    ''', (job_id,)).fetchall()
    conn.close()
    
    return render_template('applications.html', job=job, applications=applications)

@app.route('/applications/<int:app_id>/update_status', methods=['POST'])
def update_application_status(app_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    status = request.json.get('status')
    
    conn = get_db()
    
    # Verify user owns the job this application belongs to
    app = conn.execute('''
        SELECT a.*, j.posted_by 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ?
    ''', (app_id,)).fetchone()
    
    if not app or app['posted_by'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn.execute('UPDATE applications SET status = ? WHERE id = ?', (status, app_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/applications/<int:app_id>/shortlist', methods=['POST'])
def ai_shortlist(app_id):
    """AI-powered shortlist button"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    
    # Verify user owns the job
    app = conn.execute('''
        SELECT a.*, j.posted_by, j.requirements, j.title 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ?
    ''', (app_id,)).fetchone()
    
    if not app or app['posted_by'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Re-screen the resume with AI
    screening_result = screener.screen_resume(
        app['resume_path'], 
        app['requirements'],
        app['title']
    )
    
    # Auto-shortlist if score >= 60%
    new_status = 'shortlisted' if screening_result['match_score'] >= 60 else 'rejected'
    
    conn.execute('''
        UPDATE applications 
        SET status = ?, screening_result = ?
        WHERE id = ?
    ''', (new_status, json.dumps(screening_result), app_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'status': new_status,
        'match_score': screening_result['match_score'],
        'recommendation': screening_result['recommendation']
    })

@app.route('/download-resume/<int:app_id>')
def download_resume(app_id):
    """Download resume - only for job owner"""
    if 'user_id' not in session:
        flash('Please login', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    app = conn.execute('''
        SELECT a.resume_path, j.posted_by 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ?
    ''', (app_id,)).fetchone()
    conn.close()
    
    if not app or app['posted_by'] != session['user_id']:
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    
    return send_file(app['resume_path'], as_attachment=True)

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    # Get analytics for user's jobs only
    applications_by_status = conn.execute('''
        SELECT a.status, COUNT(*) as count 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.posted_by = ?
        GROUP BY a.status
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('analytics.html', applications_by_status=applications_by_status)

os.makedirs('resumes', exist_ok=True)
init_db()

if __name__ == "__main__":
    app.run()
