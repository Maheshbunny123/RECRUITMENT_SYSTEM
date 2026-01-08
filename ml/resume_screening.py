import re
import os
from pathlib import Path
import PyPDF2
import docx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

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
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def extract_text_from_docx(self, docx_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(docx_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""
    
    def extract_text_from_txt(self, txt_path):
        """Extract text from TXT file"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading TXT: {e}")
            return ""
    
    def extract_text(self, file_path):
        """Extract text based on file extension"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            return self.extract_text_from_docx(file_path)
        elif ext == '.txt':
            return self.extract_text_from_txt(file_path)
        else:
            return ""
    
    def extract_email(self, text):
        """Extract email from resume text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else None
    
    def extract_phone(self, text):
        """Extract phone number from resume text"""
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        phones = re.findall(phone_pattern, text)
        return phones[0] if phones else None
    
    def extract_skills(self, text):
        """Extract skills from resume text"""
        text_lower = text.lower()
        found_skills = []
        skill_categories = {}
        
        for category, skills in self.skills_database.items():
            category_skills = []
            for skill in skills:
                if skill.lower() in text_lower:
                    found_skills.append(skill)
                    category_skills.append(skill)
            
            if category_skills:
                skill_categories[category] = category_skills
        
        return found_skills, skill_categories
    
    def extract_experience(self, text):
        """Extract years of experience from resume"""
        # Look for patterns like "5 years", "5+ years", "5-7 years"
        experience_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of)?\s*(?:experience|exp)',
            r'experience\s*:\s*(\d+)\+?\s*years?',
            r'(\d+)\s*-\s*(\d+)\s*years?\s*(?:of)?\s*(?:experience|exp)'
        ]
        
        max_experience = 0
        text_lower = text.lower()
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    # For range patterns, take the maximum
                    exp = max([int(x) for x in match if x.isdigit()])
                else:
                    exp = int(match)
                max_experience = max(max_experience, exp)
        
        return max_experience
    
    def extract_education(self, text):
        """Extract education level from resume"""
        text_lower = text.lower()
        highest_level = 0
        highest_degree = "Unknown"
        
        for degree, level in self.education_levels.items():
            if degree in text_lower:
                if level > highest_level:
                    highest_level = level
                    highest_degree = degree.title()
        
        return highest_degree, highest_level
    
    def calculate_match_score(self, resume_text, job_requirements, job_title):
        """Calculate match score between resume and job requirements using TF-IDF"""
        # Combine job title and requirements for better matching
        job_text = f"{job_title} {job_requirements}"
        
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
        
        try:
            # Fit and transform the texts
            tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Convert to percentage (0-100)
            match_score = round(similarity * 100, 2)
            
        except Exception as e:
            print(f"Error calculating match score: {e}")
            match_score = 0
        
        return match_score
    
    def screen_resume(self, resume_path, job_requirements, job_title=""):
        """Main method to screen a resume"""
        # Extract text from resume
        resume_text = self.extract_text(resume_path)
        
        if not resume_text:
            return {
                'error': 'Could not extract text from resume',
                'match_score': 0
            }
        
        # Extract information
        email = self.extract_email(resume_text)
        phone = self.extract_phone(resume_text)
        skills, skill_categories = self.extract_skills(resume_text)
        experience_years = self.extract_experience(resume_text)
        education_level, education_score = self.extract_education(resume_text)
        
        # Calculate match score
        match_score = self.calculate_match_score(resume_text, job_requirements, job_title)
        
        # Extract required skills from job requirements
        required_skills, req_skill_categories = self.extract_skills(job_requirements)
        
        # Calculate skill match percentage
        if required_skills:
            matched_skills = set(skills) & set(required_skills)
            skill_match_percentage = (len(matched_skills) / len(required_skills)) * 100
        else:
            matched_skills = set(skills)
            skill_match_percentage = 50  # Default if no specific skills required
        
        # Adjust match score based on various factors
        final_score = match_score
        
        # Bonus for matching skills
        final_score += skill_match_percentage * 0.2
        
        # Bonus for relevant experience
        if experience_years >= 3:
            final_score += 5
        if experience_years >= 5:
            final_score += 5
        
        # Bonus for education
        if education_score >= 3:
            final_score += 5
        if education_score >= 4:
            final_score += 5
        
        # Cap the score at 100
        final_score = min(final_score, 100)
        
        # Determine recommendation
        if final_score >= 75:
            recommendation = "Highly Recommended"
        elif final_score >= 60:
            recommendation = "Recommended"
        elif final_score >= 45:
            recommendation = "Maybe"
        else:
            recommendation = "Not Recommended"
        
        return {
            'match_score': round(final_score, 2),
            'email': email,
            'phone': phone,
            'skills_matched': list(matched_skills),
            'all_skills': skills,
            'skill_categories': skill_categories,
            'required_skills': required_skills,
            'skill_match_percentage': round(skill_match_percentage, 2),
            'experience_years': experience_years,
            'education_level': education_level,
            'education_score': education_score,
            'recommendation': recommendation,
            'resume_text_length': len(resume_text),
            'extracted_successfully': True
        }
    
    def analyze_resume_quality(self, resume_path):
        """Analyze resume quality and provide scoring"""
        resume_text = self.extract_text(resume_path)
        
        if not resume_text:
            return {'error': 'Could not extract text', 'total_score': 0}
        
        scores = {}
        
        # 1. Length Score (15 points)
        word_count = len(resume_text.split())
        if word_count >= 400:
            scores['length'] = 15
        elif word_count >= 250:
            scores['length'] = 10
        elif word_count >= 150:
            scores['length'] = 5
        else:
            scores['length'] = 0
        
        # 2. Contact Info Score (10 points)
        email = self.extract_email(resume_text)
        phone = self.extract_phone(resume_text)
        scores['contact'] = (5 if email else 0) + (5 if phone else 0)
        
        # 3. Skills Score (25 points)
        skills, _ = self.extract_skills(resume_text)
        if len(skills) >= 10:
            scores['skills'] = 25
        elif len(skills) >= 6:
            scores['skills'] = 20
        elif len(skills) >= 3:
            scores['skills'] = 15
        else:
            scores['skills'] = 5
        
        # 4. Experience Score (20 points)
        exp_years = self.extract_experience(resume_text)
        if exp_years >= 5:
            scores['experience'] = 20
        elif exp_years >= 3:
            scores['experience'] = 15
        elif exp_years >= 1:
            scores['experience'] = 10
        else:
            scores['experience'] = 5
        
        # 5. Education Score (15 points)
        _, edu_level = self.extract_education(resume_text)
        if edu_level >= 4:
            scores['education'] = 15
        elif edu_level >= 3:
            scores['education'] = 12
        elif edu_level >= 2:
            scores['education'] = 8
        else:
            scores['education'] = 3
        
        # 6. Structure Score (15 points)
        structure_score = 0
        keywords = ['experience', 'education', 'skills', 'summary', 'objective', 'project']
        for keyword in keywords:
            if keyword in resume_text.lower():
                structure_score += 2.5
        scores['structure'] = min(structure_score, 15)
        
        total = sum(scores.values())
        
        # Grade
        if total >= 85:
            grade = 'A+'
            feedback = 'Excellent resume! Very well structured and comprehensive.'
        elif total >= 75:
            grade = 'A'
            feedback = 'Great resume! Strong content with minor improvements possible.'
        elif total >= 65:
            grade = 'B'
            feedback = 'Good resume! Consider adding more relevant skills or experience.'
        elif total >= 50:
            grade = 'C'
            feedback = 'Average resume. Needs significant improvements in multiple areas.'
        else:
            grade = 'D'
            feedback = 'Weak resume. Major improvements needed in content and structure.'
        
        return {
            'total_score': round(total, 2),
            'grade': grade,
            'scores': scores,
            'feedback': feedback,
            'word_count': word_count,
            'skills_found': len(skills),
            'experience_years': exp_years,
            'has_email': bool(email),
            'has_phone': bool(phone),
            'improvements': self._get_improvements(scores)
        }
    
    def _get_improvements(self, scores):
        """Get improvement suggestions"""
        improvements = []
        
        if scores['length'] < 10:
            improvements.append('Increase content: Add more details about your experience and achievements (aim for 250-400 words).')
        if scores['contact'] < 10:
            improvements.append('Add complete contact information: Include both email and phone number.')
        if scores['skills'] < 20:
            improvements.append('List more skills: Add technical and soft skills relevant to your field (aim for 8-12 skills).')
        if scores['experience'] < 15:
            improvements.append('Highlight experience: Provide more details about your work history and years of experience.')
        if scores['education'] < 12:
            improvements.append('Include education: Add your degree, institution, and graduation year.')
        if scores['structure'] < 12:
            improvements.append('Improve structure: Use clear sections like Summary, Experience, Education, Skills, Projects.')
        
        return improvements

# Testing function
if __name__ == "__main__":
    screener = ResumeScreener()
    
    # Test with a sample job requirement
    job_req = """
    We are looking for a Python Developer with 3+ years of experience.
    Required skills: Python, Django, Flask, SQL, REST API, Git
    Good to have: AWS, Docker, Machine Learning
    Education: Bachelor's degree in Computer Science or related field
    """
    
    # This is just for testing - in production, provide actual resume path
    print("Resume Screener initialized successfully!")
    print("Skills database loaded with", sum(len(v) for v in screener.skills_database.values()), "skills")