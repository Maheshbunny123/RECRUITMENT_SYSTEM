from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from ml.resume_screening import ResumeScreener

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'resumes'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

# Initialize resume screener
screener = ResumeScreener()

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            requirements TEXT NOT NULL,
            recruiter_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recruiter_id) REFERENCES users (id)
        )
    ''')
    
    # Applications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            jobseeker_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            resume_path TEXT NOT NULL,
            cover_letter TEXT,
            match_score REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id),
            FOREIGN KEY (jobseeker_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ==================== LANDING PAGE ====================
@app.route('/')
def landing():
    return render_template('landing.html')

# ==================== JOB SEEKER ROUTES ====================
@app.route('/jobseeker/register', methods=['GET', 'POST'])
def jobseeker_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        phone = request.form.get('phone', '')
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db()
            conn.execute('''
                INSERT INTO users (username, password, email, name, phone, role)
                VALUES (?, ?, ?, ?, ?, 'jobseeker')
            ''', (username, hashed_password, email, name, phone))
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('jobseeker_login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'danger')
    
    return render_template('jobseeker_register.html')

@app.route('/jobseeker/login', methods=['GET', 'POST'])
def jobseeker_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND role = "jobseeker"', 
                          (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = 'jobseeker'
            flash('Login successful!', 'success')
            return redirect(url_for('jobseeker_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('jobseeker_login.html')

@app.route('/jobseeker/dashboard')
def jobseeker_dashboard():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('jobseeker_login'))
    
    conn = get_db()
    
    # Get statistics
    stats = {
        'total_applications': conn.execute('SELECT COUNT(*) as count FROM applications WHERE jobseeker_id = ?', 
                                         (session['user_id'],)).fetchone()['count'],
        'pending': conn.execute('SELECT COUNT(*) as count FROM applications WHERE jobseeker_id = ? AND status = "Pending"', 
                              (session['user_id'],)).fetchone()['count'],
        'shortlisted': conn.execute('SELECT COUNT(*) as count FROM applications WHERE jobseeker_id = ? AND status = "Shortlisted"', 
                                  (session['user_id'],)).fetchone()['count'],
        'available_jobs': conn.execute('SELECT COUNT(*) as count FROM jobs').fetchone()['count']
    }
    
    # Get recent jobs
    recent_jobs = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 4').fetchall()
    conn.close()
    
    return render_template('jobseeker_dashboard.html', stats=stats, recent_jobs=recent_jobs)

@app.route('/jobseeker/browse-jobs')
def browse_jobs():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('jobseeker_login'))
    
    conn = get_db()
    jobs = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('browse_jobs.html', jobs=jobs)

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply_job(job_id):
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('jobseeker_login'))
    
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        cover_letter = request.form.get('cover_letter', '')
        
        if 'resume' not in request.files:
            flash('No resume file!', 'danger')
            return redirect(request.url)
        
        file = request.files['resume']
        
        if file.filename == '':
            flash('No selected file!', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{session['user_id']}_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Calculate match score
            job_description = f"{job['title']} {job['description']} {job['requirements']}"
            match_score = screener.screen_resume(filepath, job_description)
            
            # Save application
            conn.execute('''
                INSERT INTO applications (job_id, jobseeker_id, name, email, phone, resume_path, cover_letter, match_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (job_id, session['user_id'], name, email, phone, filepath, cover_letter, match_score))
            conn.commit()
            conn.close()
            
            flash(f'Application submitted! Your match score: {match_score}%', 'success')
            return redirect(url_for('my_applications'))
    
    conn.close()
    return render_template('apply_job.html', job=job)

@app.route('/jobseeker/my-applications')
def my_applications():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('jobseeker_login'))
    
    conn = get_db()
    applications = conn.execute('''
        SELECT a.*, j.title as job_title, j.company 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id 
        WHERE a.jobseeker_id = ?
        ORDER BY a.applied_date DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('my_applications.html', applications=applications)

@app.route('/jobseeker/resume-scorer', methods=['GET', 'POST'])
def resume_scorer():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('jobseeker_login'))
    
    score = None
    
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No resume file!', 'danger')
            return redirect(request.url)
        
        file = request.files['resume']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(f"temp_{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get quality score
            score = screener.get_resume_quality_score(filepath)
            
            # Clean up temp file
            os.remove(filepath)
    
    return render_template('resume_scorer.html', score=score)

@app.route('/jobseeker/job-matcher', methods=['GET', 'POST'])
def job_matcher():
    if 'user_id' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('jobseeker_login'))
    
    match = None
    
    if request.method == 'POST':
        job_description = request.form['job_description']
        
        if 'resume' not in request.files:
            flash('No resume file!', 'danger')
            return redirect(request.url)
        
        file = request.files['resume']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(f"temp_{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get detailed match analysis
            match = screener.compare_resume_job(filepath, job_description)
            
            # Clean up temp file
            os.remove(filepath)
    
    return render_template('job_matcher.html', match=match)

# ==================== RECRUITER ROUTES ====================
@app.route('/recruiter/register', methods=['GET', 'POST'])
def recruiter_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        company = request.form.get('company', '')
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db()
            conn.execute('''
                INSERT INTO users (username, password, email, name, phone, role)
                VALUES (?, ?, ?, ?, ?, 'recruiter')
            ''', (username, hashed_password, email, name, company))
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('recruiter_login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'danger')
    
    return render_template('recruiter_register.html')

@app.route('/recruiter/login', methods=['GET', 'POST'])
def recruiter_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND role = "recruiter"', 
                          (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = 'recruiter'
            flash('Login successful!', 'success')
            return redirect(url_for('recruiter_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('recruiter_login.html')

@app.route('/recruiter/dashboard')
def recruiter_dashboard():
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('recruiter_login'))
    
    conn = get_db()
    
    # Get statistics
    stats = {
        'total_jobs': conn.execute('SELECT COUNT(*) as count FROM jobs WHERE recruiter_id = ?', 
                                  (session['user_id'],)).fetchone()['count'],
        'total_applications': conn.execute('''
            SELECT COUNT(*) as count FROM applications a 
            JOIN jobs j ON a.job_id = j.id 
            WHERE j.recruiter_id = ?
        ''', (session['user_id'],)).fetchone()['count'],
        'pending': conn.execute('''
            SELECT COUNT(*) as count FROM applications a 
            JOIN jobs j ON a.job_id = j.id 
            WHERE j.recruiter_id = ? AND a.status = "Pending"
        ''', (session['user_id'],)).fetchone()['count'],
        'shortlisted': conn.execute('''
            SELECT COUNT(*) as count FROM applications a 
            JOIN jobs j ON a.job_id = j.id 
            WHERE j.recruiter_id = ? AND a.status = "Shortlisted"
        ''', (session['user_id'],)).fetchone()['count']
    }
    
    # Get recent jobs
    recent_jobs = conn.execute('SELECT * FROM jobs WHERE recruiter_id = ? ORDER BY created_at DESC LIMIT 5', 
                              (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', stats=stats, recent_jobs=recent_jobs)

@app.route('/recruiter/create-job', methods=['GET', 'POST'])
def create_job():
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('recruiter_login'))
    
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        description = request.form['description']
        requirements = request.form['requirements']
        
        conn = get_db()
        conn.execute('''
            INSERT INTO jobs (title, company, location, description, requirements, recruiter_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, company, location, description, requirements, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Job posted successfully!', 'success')
        return redirect(url_for('recruiter_dashboard'))
    
    return render_template('create_job.html')

@app.route('/recruiter/applications/<int:job_id>')
def view_applications(job_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('recruiter_login'))
    
    conn = get_db()
    
    # Verify job belongs to recruiter
    job = conn.execute('SELECT * FROM jobs WHERE id = ? AND recruiter_id = ?', 
                      (job_id, session['user_id'])).fetchone()
    
    if not job:
        flash('Job not found!', 'danger')
        return redirect(url_for('recruiter_dashboard'))
    
    # Get applications
    applications = conn.execute('''
        SELECT * FROM applications WHERE job_id = ? ORDER BY match_score DESC
    ''', (job_id,)).fetchall()
    conn.close()
    
    return render_template('applications.html', job=job, applications=applications)

@app.route('/recruiter/ai-shortlist/<int:application_id>')
def ai_shortlist(application_id):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('recruiter_login'))
    
    conn = get_db()
    
    application = conn.execute('''
        SELECT a.*, j.recruiter_id 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id 
        WHERE a.id = ?
    ''', (application_id,)).fetchone()
    
    if not application or application['recruiter_id'] != session['user_id']:
        flash('Application not found!', 'danger')
        return redirect(url_for('recruiter_dashboard'))
    
    # AI decision based on match score
    if application['match_score'] >= 60:
        new_status = 'Shortlisted'
        message = f"✅ Candidate shortlisted! Match score: {application['match_score']}%"
    else:
        new_status = 'Rejected'
        message = f"❌ Candidate rejected. Match score: {application['match_score']}%"
    
    conn.execute('UPDATE applications SET status = ? WHERE id = ?', 
                (new_status, application_id))
    conn.commit()
    conn.close()
    
    flash(message, 'success')
    return redirect(url_for('view_applications', job_id=application['job_id']))

@app.route('/recruiter/update-status/<int:application_id>/<status>')
def update_status(application_id, status):
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('recruiter_login'))
    
    conn = get_db()
    application = conn.execute('''
        SELECT a.*, j.recruiter_id 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id 
        WHERE a.id = ?
    ''', (application_id,)).fetchone()
    
    if application and application['recruiter_id'] == session['user_id']:
        conn.execute('UPDATE applications SET status = ? WHERE id = ?', 
                    (status, application_id))
        conn.commit()
        flash(f'Status updated to {status}!', 'success')
    
    conn.close()
    return redirect(request.referrer)

@app.route('/recruiter/analytics')
def analytics():
    if 'user_id' not in session or session.get('role') != 'recruiter':
        return redirect(url_for('recruiter_login'))
    
    conn = get_db()
    
    # Get analytics data
    jobs = conn.execute('SELECT * FROM jobs WHERE recruiter_id = ?', 
                       (session['user_id'],)).fetchall()
    
    applications_by_status = conn.execute('''
        SELECT a.status, COUNT(*) as count 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id 
        WHERE j.recruiter_id = ? 
        GROUP BY a.status
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('analytics.html', jobs=jobs, applications_by_status=applications_by_status)

# ==================== COMMON ROUTES ====================
@app.route('/download-resume/<filename>')
def download_resume(filename):
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('landing'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
