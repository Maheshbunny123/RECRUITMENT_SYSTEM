"""
Generate test data and sample resumes for testing the recruitment system
Run this script to create sample jobs and test resumes
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def create_sample_resume_pdf(filename, data):
    """Create a sample resume PDF for testing"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1*inch, height - 1*inch, data['name'])
    
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, height - 1.3*inch, data['email'])
    c.drawString(1*inch, height - 1.5*inch, data['phone'])
    
    # Professional Summary
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, height - 2*inch, "Professional Summary")
    c.setFont("Helvetica", 11)
    
    summary_lines = data['summary'].split('. ')
    y_position = height - 2.3*inch
    for line in summary_lines:
        c.drawString(1*inch, y_position, line + '.')
        y_position -= 0.2*inch
    
    # Skills
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y_position - 0.3*inch, "Technical Skills")
    y_position -= 0.6*inch
    
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, y_position, data['skills'])
    y_position -= 0.3*inch
    
    # Experience
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y_position - 0.3*inch, "Work Experience")
    y_position -= 0.6*inch
    
    for exp in data['experience']:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y_position, exp['title'])
        y_position -= 0.2*inch
        
        c.setFont("Helvetica", 11)
        c.drawString(1*inch, y_position, f"{exp['company']} | {exp['duration']}")
        y_position -= 0.2*inch
        
        for resp in exp['responsibilities']:
            c.drawString(1.2*inch, y_position, f"• {resp}")
            y_position -= 0.2*inch
        y_position -= 0.1*inch
    
    # Education
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y_position - 0.2*inch, "Education")
    y_position -= 0.5*inch
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y_position, data['education']['degree'])
    y_position -= 0.2*inch
    
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, y_position, f"{data['education']['university']} | {data['education']['year']}")
    
    c.save()
    print(f"Created: {filename}")

def generate_test_resumes():
    """Generate multiple test resumes with different profiles"""
    
    os.makedirs('test_resumes', exist_ok=True)
    
    # High Match Resume - Senior Python Developer
    resume1 = {
        'name': 'John Smith',
        'email': 'john.smith@email.com',
        'phone': '+1 (555) 123-4567',
        'summary': 'Experienced Python Developer with 5+ years of expertise in building scalable web applications. Proficient in Django, Flask, and REST API development. Strong background in machine learning and data analysis',
        'skills': 'Python, Django, Flask, REST API, SQL, PostgreSQL, Git, Docker, AWS, Machine Learning, Pandas, NumPy, JavaScript, HTML, CSS, Agile',
        'experience': [
            {
                'title': 'Senior Python Developer',
                'company': 'Tech Corp',
                'duration': '2020 - Present',
                'responsibilities': [
                    'Developed and maintained multiple Django-based web applications',
                    'Built REST APIs serving 1M+ daily requests',
                    'Implemented machine learning models for data analysis',
                    'Mentored junior developers and conducted code reviews'
                ]
            },
            {
                'title': 'Python Developer',
                'company': 'Software Solutions Inc',
                'duration': '2018 - 2020',
                'responsibilities': [
                    'Created Flask microservices for e-commerce platform',
                    'Optimized database queries reducing response time by 40%',
                    'Integrated third-party APIs and payment gateways'
                ]
            }
        ],
        'education': {
            'degree': 'Bachelor of Science in Computer Science',
            'university': 'State University',
            'year': '2018'
        }
    }
    
    # Medium Match Resume - Junior Developer
    resume2 = {
        'name': 'Sarah Johnson',
        'email': 'sarah.johnson@email.com',
        'phone': '+1 (555) 234-5678',
        'summary': 'Motivated Computer Science graduate with 2 years of experience in web development. Skilled in Python, JavaScript, and database management. Quick learner with passion for technology',
        'skills': 'Python, JavaScript, HTML, CSS, React, Node.js, SQL, Git, RESTful APIs',
        'experience': [
            {
                'title': 'Junior Web Developer',
                'company': 'Digital Agency',
                'duration': '2022 - Present',
                'responsibilities': [
                    'Developed responsive web applications using React and Node.js',
                    'Collaborated with design team to implement UI/UX improvements',
                    'Maintained and updated existing Python scripts'
                ]
            },
            {
                'title': 'Intern Developer',
                'company': 'StartUp Co',
                'duration': '2021 - 2022',
                'responsibilities': [
                    'Assisted in building company website using HTML, CSS, JavaScript',
                    'Learned version control with Git',
                    'Participated in daily stand-ups and agile ceremonies'
                ]
            }
        ],
        'education': {
            'degree': 'Bachelor of Science in Computer Science',
            'university': 'Tech University',
            'year': '2021'
        }
    }
    
    # Low Match Resume - Different Field
    resume3 = {
        'name': 'Michael Brown',
        'email': 'michael.brown@email.com',
        'phone': '+1 (555) 345-6789',
        'summary': 'Experienced Data Analyst with strong Excel and SQL skills. Background in business intelligence and reporting. Looking to transition into development roles',
        'skills': 'Excel, SQL, Tableau, Power BI, Data Analysis, Business Intelligence, R, Statistics',
        'experience': [
            {
                'title': 'Data Analyst',
                'company': 'Finance Corp',
                'duration': '2019 - Present',
                'responsibilities': [
                    'Created complex Excel spreadsheets and dashboards',
                    'Wrote SQL queries for data extraction and reporting',
                    'Developed Tableau visualizations for stakeholders',
                    'Analyzed business metrics and KPIs'
                ]
            },
            {
                'title': 'Business Analyst',
                'company': 'Consulting Firm',
                'duration': '2017 - 2019',
                'responsibilities': [
                    'Gathered business requirements from clients',
                    'Created process documentation and workflows',
                    'Conducted data analysis using Excel and SQL'
                ]
            }
        ],
        'education': {
            'degree': 'Bachelor of Business Administration',
            'university': 'Business School',
            'year': '2017'
        }
    }
    
    # Create PDFs
    create_sample_resume_pdf('test_resumes/john_smith_senior_python.pdf', resume1)
    create_sample_resume_pdf('test_resumes/sarah_johnson_junior_dev.pdf', resume2)
    create_sample_resume_pdf('test_resumes/michael_brown_data_analyst.pdf', resume3)
    
    print("\n✅ Test resumes created successfully!")
    print("Location: test_resumes/")
    print("\nTest these resumes with different job requirements to see varying match scores:")
    print("1. john_smith_senior_python.pdf - Expected: 75-90% match for Python jobs")
    print("2. sarah_johnson_junior_dev.pdf - Expected: 50-70% match for Python jobs")
    print("3. michael_brown_data_analyst.pdf - Expected: 30-50% match for Python jobs")

def print_sample_job_descriptions():
    """Print sample job descriptions for testing"""
    print("\n" + "="*60)
    print("SAMPLE JOB DESCRIPTIONS FOR TESTING")
    print("="*60)
    
    print("\n1. SENIOR PYTHON DEVELOPER")
    print("-" * 40)
    print("""
Title: Senior Python Developer

Description:
We are looking for an experienced Python Developer to join our growing team. 
You will be responsible for developing and maintaining high-quality web applications
using Django and Flask frameworks.

Requirements:
- 5+ years of Python development experience
- Strong expertise in Django and Flask frameworks
- Experience with REST API development
- Proficiency in SQL and PostgreSQL
- Knowledge of Git, Docker, and AWS
- Bachelor's degree in Computer Science or related field
- Experience with Agile methodologies

Nice to have:
- Machine learning experience
- Knowledge of React or Vue.js
- DevOps experience
    """)
    
    print("\n2. JUNIOR FULL STACK DEVELOPER")
    print("-" * 40)
    print("""
Title: Junior Full Stack Developer

Description:
We're seeking a motivated Junior Developer to work on our web applications.
This is a great opportunity for someone looking to grow their career in software development.

Requirements:
- 1-2 years of programming experience
- Knowledge of Python, JavaScript, or similar languages
- Basic understanding of HTML, CSS, and web technologies
- Familiarity with SQL databases
- Bachelor's degree in Computer Science
- Good communication skills
- Willingness to learn new technologies

Nice to have:
- Experience with React or other modern frameworks
- Understanding of Git version control
- Exposure to Agile development
    """)

if __name__ == "__main__":
    print("="*60)
    print("RECRUITMENT SYSTEM - TEST DATA GENERATOR")
    print("="*60)
    
    # Check if reportlab is installed
    try:
        import reportlab
        generate_test_resumes()
        print_sample_job_descriptions()
        
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("1. Start the Flask application: python app.py")
        print("2. Login with: admin / admin123")
        print("3. Create a job using the sample descriptions above")
        print("4. Upload the test resumes from test_resumes/ folder")
        print("5. Check the match scores and screening results")
        print("\n✨ Happy Testing!")
        
    except ImportError:
        print("\n⚠️  ReportLab not installed!")
        print("Install it with: pip install reportlab")
        print("\nOr create test resumes manually with these profiles:")
        print_sample_job_descriptions()
        print("\nCreate text files or Word documents with similar content.")