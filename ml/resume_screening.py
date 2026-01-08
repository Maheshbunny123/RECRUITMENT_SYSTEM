import re
from pathlib import Path
import PyPDF2
import docx

class ResumeScreener:
    def __init__(self):
        self.skills_database = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust', 'typescript'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'express', 'fastapi'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'redis', 'cassandra', 'dynamodb', 'sqlite'],
            'ml_ai': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn', 'keras', 'nlp', 'computer vision', 'neural networks'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'ci/cd', 'terraform', 'ansible'],
            'mobile': ['android', 'ios', 'react native', 'flutter', 'swift', 'kotlin', 'xamarin'],
            'data': ['data analysis', 'data science', 'pandas', 'numpy', 'matplotlib', 'tableau', 'power bi', 'excel', 'r'],
            'tools': ['git', 'github', 'jira', 'agile', 'scrum', 'linux', 'unix', 'bash', 'api', 'rest', 'graphql']
        }
        
        self.education_levels = {
            'phd': 5, 'ph.d': 5, 'doctorate': 5,
            'masters': 4, 'master': 4, 'msc': 4, 'm.sc': 4, 'mba': 4, 'ms': 4,
            'bachelors': 3, 'bachelor': 3, 'bsc': 3, 'b.sc': 3, 'btech': 3, 'b.tech': 3, 'be': 3, 'b.e': 3, 'ba': 3,
            'diploma': 2,
            'high school': 1, 'secondary': 1
        }

    # ------------------ TEXT EXTRACTION ------------------ #
    def extract_text_from_pdf(self, pdf_path):
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def extract_text_from_docx(self, docx_path):
        try:
            doc = docx.Document(docx_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""
    
    def extract_text_from_txt(self, txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading TXT: {e}")
            return ""
    
    def extract_text(self, file_path):
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            return self.extract_text_from_docx(file_path)
        elif ext == '.txt':
            return self.extract_text_from_txt(file_path)
        else:
            return ""
    
    # ------------------ INFORMATION EXTRACTION ------------------ #
    def extract_email(self, text):
        matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
        return matches[0] if matches else None
    
    def extract_phone(self, text):
        matches = re.findall(r'[\+\(]?[0-9][0-9 .\-\(\)]{8,}[0-9]', text)
        return matches[0] if matches else None
    
    def extract_skills(self, text):
        text_lower = text.lower()
        found_skills = []
        skill_categories = {}
        for cat, skills in self.skills_database.items():
            cat_skills = []
            for skill in skills:
                if skill.lower() in text_lower:
                    found_skills.append(skill)
                    cat_skills.append(skill)
            if cat_skills:
                skill_categories[cat] = cat_skills
        return found_skills, skill_categories
    
    def extract_experience(self, text):
        text_lower = text.lower()
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of)?\s*(?:experience|exp)',
            r'experience\s*:\s*(\d+)\+?\s*years?',
            r'(\d+)\s*-\s*(\d+)\s*years?\s*(?:of)?\s*(?:experience|exp)'
        ]
        max_exp = 0
        for pat in patterns:
            matches = re.findall(pat, text_lower)
            for m in matches:
                if isinstance(m, tuple):
                    exp = max(int(x) for x in m if x.isdigit())
                else:
                    exp = int(m)
                max_exp = max(max_exp, exp)
        return max_exp
    
    def extract_education(self, text):
        text_lower = text.lower()
        highest_level = 0
        highest_degree = "Unknown"
        for degree, level in self.education_levels.items():
            if degree in text_lower and level > highest_level:
                highest_level = level
                highest_degree = degree.title()
        return highest_degree, highest_level

    # ------------------ MATCH SCORING WITHOUT SKLEARN ------------------ #
    def calculate_match_score(self, resume_text, job_requirements, job_title=""):
        # Simple keyword overlap
        resume_words = set(resume_text.lower().split())
        job_words = set((job_title + " " + job_requirements).lower().split())
        if not job_words:
            return 0
        overlap = resume_words & job_words
        score = (len(overlap) / len(job_words)) * 100
        return round(score, 2)
    
    # ------------------ RESUME SCREENING ------------------ #
    def screen_resume(self, resume_path, job_requirements, job_title=""):
        text = self.extract_text(resume_path)
        if not text:
            return {'error': 'Could not extract text', 'match_score': 0}
        
        email = self.extract_email(text)
        phone = self.extract_phone(text)
        skills, skill_cats = self.extract_skills(text)
        experience = self.extract_experience(text)
        education, edu_score = self.extract_education(text)
        
        match_score = self.calculate_match_score(text, job_requirements, job_title)
        
        required_skills, _ = self.extract_skills(job_requirements)
        if required_skills:
            matched_skills = set(skills) & set(required_skills)
            skill_match_pct = (len(matched_skills) / len(required_skills)) * 100
        else:
            matched_skills = set(skills)
            skill_match_pct = 50
        
        # Adjust score
        final_score = match_score + skill_match_pct * 0.2
        if experience >= 3: final_score += 5
        if experience >= 5: final_score += 5
        if edu_score >= 3: final_score += 5
        if edu_score >= 4: final_score += 5
        final_score = min(final_score, 100)
        
        # Recommendation
        if final_score >= 75: rec = "Highly Recommended"
        elif final_score >= 60: rec = "Recommended"
        elif final_score >= 45: rec = "Maybe"
        else: rec = "Not Recommended"
        
        return {
            'match_score': round(final_score, 2),
            'email': email,
            'phone': phone,
            'skills_matched': list(matched_skills),
            'all_skills': skills,
            'skill_categories': skill_cats,
            'required_skills': required_skills,
            'skill_match_percentage': round(skill_match_pct, 2),
            'experience_years': experience,
            'education_level': education,
            'education_score': edu_score,
            'recommendation': rec,
            'resume_text_length': len(text),
            'extracted_successfully': True
        }

# ------------------ TEST ------------------ #
if __name__ == "__main__":
    screener = ResumeScreener()
    job_req = """
    Python Developer with 3+ years experience.
    Required: Python, Django, Flask, SQL, REST API, Git
    Good to have: AWS, Docker, Machine Learning
    Education: Bachelor's in CS or related
    """
    print("Resume Screener initialized!")
    print("Skills database loaded with", sum(len(v) for v in screener.skills_database.values()), "skills")
