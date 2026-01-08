import re
import PyPDF2
import docx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class ResumeScreener:
    def __init__(self):
        self.skills_database = [
            # Programming Languages
            'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go',
            'rust', 'typescript', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash',
            
            # Web Technologies
            'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
            'spring', 'asp.net', 'jquery', 'bootstrap', 'tailwind', 'sass', 'webpack',
            
            # Databases
            'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'redis', 'cassandra', 'dynamodb',
            'elasticsearch', 'sqlite', 'mariadb', 'neo4j',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'github', 'gitlab',
            'ci/cd', 'terraform', 'ansible', 'chef', 'puppet', 'circleci',
            
            # Data Science & AI
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
            'pandas', 'numpy', 'data analysis', 'nlp', 'computer vision', 'opencv',
            
            # Other Skills
            'agile', 'scrum', 'jira', 'rest api', 'graphql', 'microservices', 'testing',
            'unit testing', 'integration testing', 'selenium', 'pytest', 'junit',
            'communication', 'leadership', 'problem solving', 'teamwork', 'project management'
        ]
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""
    
    def extract_text_from_txt(self, file_path):
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading TXT: {e}")
            return ""
    
    def extract_text(self, file_path):
        """Extract text based on file extension"""
        if file_path.endswith('.pdf'):
            return self.extract_text_from_pdf(file_path)
        elif file_path.endswith('.docx'):
            return self.extract_text_from_docx(file_path)
        elif file_path.endswith('.txt'):
            return self.extract_text_from_txt(file_path)
        else:
            return ""
    
    def extract_skills(self, text):
        """Extract skills from text"""
        text_lower = text.lower()
        found_skills = []
        
        for skill in self.skills_database:
            if skill.lower() in text_lower:
                found_skills.append(skill.title())
        
        return list(set(found_skills))  # Remove duplicates
    
    def extract_experience(self, text):
        """Extract years of experience"""
        patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
            r'experience\s*(?:of)?\s*(\d+)\+?\s*(?:years?|yrs?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}+ years"
        
        return "Not specified"
    
    def extract_education(self, text):
        """Extract education level"""
        education_keywords = {
            'PhD': ['phd', 'ph.d', 'doctorate'],
            'Masters': ['masters', 'master', 'm.s', 'msc', 'm.tech', 'mba'],
            'Bachelors': ['bachelors', 'bachelor', 'b.s', 'bsc', 'b.tech', 'b.e', 'bba'],
            'Diploma': ['diploma', 'associate']
        }
        
        text_lower = text.lower()
        
        for level, keywords in education_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return level
        
        return "Not specified"
    
    def screen_resume(self, resume_path, job_description):
        """
        Screen resume against job description
        Returns match score (0-100)
        """
        resume_text = self.extract_text(resume_path)
        
        if not resume_text:
            return 0
        
        # Use TF-IDF and cosine similarity
        vectorizer = TfidfVectorizer(stop_words='english')
        
        try:
            tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Convert to percentage
            match_score = round(similarity * 100, 2)
            
            return match_score
        except Exception as e:
            print(f"Error in screening: {e}")
            return 0
    
    def get_resume_quality_score(self, resume_path):
        """
        Analyze resume quality and return detailed scores
        """
        text = self.extract_text(resume_path)
        
        if not text:
            return None
        
        # Extract information
        skills = self.extract_skills(text)
        experience = self.extract_experience(text)
        education = self.extract_education(text)
        
        # Calculate scores
        word_count = len(text.split())
        
        # Content score (based on word count)
        if word_count > 500:
            content_score = 100
        elif word_count > 300:
            content_score = 80
        elif word_count > 150:
            content_score = 60
        else:
            content_score = 40
        
        # Skills score (based on number of skills)
        skills_count = len(skills)
        if skills_count >= 15:
            skills_score = 100
        elif skills_count >= 10:
            skills_score = 80
        elif skills_count >= 5:
            skills_score = 60
        else:
            skills_score = 40
        
        # Experience score
        if 'Not specified' in experience:
            experience_score = 50
        else:
            years = int(re.search(r'\d+', experience).group())
            if years >= 5:
                experience_score = 100
            elif years >= 3:
                experience_score = 80
            elif years >= 1:
                experience_score = 60
            else:
                experience_score = 40
        
        # Format score (basic checks)
        has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        has_phone = bool(re.search(r'\b\d{10,}\b', text))
        has_education = education != "Not specified"
        
        format_score = 0
        if has_email:
            format_score += 33
        if has_phone:
            format_score += 33
        if has_education:
            format_score += 34
        
        # Overall score
        overall_score = round((content_score + skills_score + experience_score + format_score) / 4, 2)
        
        # Grade
        if overall_score >= 90:
            grade = 'A+'
            summary = 'Outstanding Resume!'
        elif overall_score >= 80:
            grade = 'A'
            summary = 'Excellent Resume!'
        elif overall_score >= 70:
            grade = 'B'
            summary = 'Good Resume'
        elif overall_score >= 60:
            grade = 'C'
            summary = 'Average Resume'
        else:
            grade = 'D'
            summary = 'Needs Improvement'
        
        # Suggestions
        suggestions = []
        if content_score < 80:
            suggestions.append("Add more detail to your work experience and achievements")
        if skills_score < 80:
            suggestions.append("Include more relevant technical and soft skills")
        if experience_score < 80:
            suggestions.append("Highlight your years of experience more clearly")
        if not has_email:
            suggestions.append("Add your email address")
        if not has_phone:
            suggestions.append("Add your phone number")
        if education == "Not specified":
            suggestions.append("Include your educational qualifications")
        if len(skills) < 5:
            suggestions.append("List more skills relevant to your target role")
        
        return {
            'overall_score': int(overall_score),
            'grade': grade,
            'summary': summary,
            'content_score': int(content_score),
            'skills_score': int(skills_score),
            'experience_score': int(experience_score),
            'format_score': int(format_score),
            'skills': skills[:20],  # Top 20 skills
            'experience': experience,
            'education': education,
            'suggestions': suggestions
        }
    
    def compare_resume_job(self, resume_path, job_description):
        """
        Detailed comparison between resume and job description
        """
        resume_text = self.extract_text(resume_path)
        
        if not resume_text:
            return None
        
        # Extract information from both
        candidate_skills = self.extract_skills(resume_text)
        job_skills = self.extract_skills(job_description)
        
        candidate_experience = self.extract_experience(resume_text)
        job_experience = self.extract_experience(job_description)
        
        candidate_education = self.extract_education(resume_text)
        job_education = self.extract_education(job_description)
        
        # Calculate match score
        match_score = self.screen_resume(resume_path, job_description)
        
        # Find matched and missing skills
        matched_skills = [skill for skill in candidate_skills if skill in job_skills]
        missing_skills = [skill for skill in job_skills if skill not in candidate_skills]
        
        # Recommendation
        if match_score >= 75:
            recommendation = "🌟 Highly Recommended"
            explanation = "Excellent match! This candidate has strong alignment with job requirements."
        elif match_score >= 60:
            recommendation = "✅ Recommended"
            explanation = "Good match. Candidate meets most of the job requirements."
        elif match_score >= 45:
            recommendation = "⚠️ Maybe"
            explanation = "Moderate match. Candidate has some relevant skills but may need training."
        else:
            recommendation = "❌ Not Recommended"
            explanation = "Low match. Candidate lacks several key requirements."
        
        return {
            'score': match_score,
            'recommendation': recommendation,
            'explanation': explanation,
            'candidate_skills': candidate_skills[:15],
            'job_skills': job_skills[:15],
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'candidate_experience': candidate_experience,
            'job_experience': job_experience,
            'candidate_education': candidate_education,
            'job_education': job_education
        }