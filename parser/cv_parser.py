"""
CV Parser Module
Extracts text from PDF and DOCX files using PyPDF2 and python-docx.
Includes OCR fallback for scanned PDFs using pytesseract.
Extracts structured information: email, skills, education, experience.
"""

import os
import re
import logging

# PDF handling
import PyPDF2

# DOCX handling
import docx


try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger('ai_recruitment')



TESSERACT_CMD = os.environ.get('TESSERACT_CMD', 'tesseract')
if OCR_AVAILABLE:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

POPPLER_PATH = os.environ.get('POPPLER_PATH', None)


# Common skills dictionary for extraction
COMMON_SKILLS = [
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'swift',
    'kotlin', 'ruby', 'php', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash',
    # Web Technologies
    'html', 'css', 'react', 'angular', 'vue', 'nodejs', 'django', 'flask', 'spring',
    'express', 'next.js', 'nuxt', 'bootstrap', 'tailwind', 'jquery',
    # Databases
    'sql', 'mysql', 'postgresql', 'mongodb', 'sqlite', 'redis', 'elasticsearch',
    'cassandra', 'dynamodb', 'firebase', 'oracle', 'mariadb',
    # Data Science / ML
    'pandas', 'numpy', 'scipy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras',
    'matplotlib', 'seaborn', 'plotly', 'power bi', 'tableau', 'machine learning',
    'deep learning', 'nlp', 'computer vision', 'data analysis', 'data visualization',
    'statistics', 'jupyter', 'anaconda', 'opencv',
    # Cloud / DevOps
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'github',
    'gitlab', 'terraform', 'ansible', 'nginx', 'apache', 'linux', 'ci/cd',
    # Mobile
    'android', 'ios', 'flutter', 'react native', 'xamarin', 'ionic',
    # Other
    'rest api', 'graphql', 'json', 'xml', 'soap', 'microservices', 'agile', 'scrum',
    'jira', 'confluence', 'figma', 'photoshop', 'illustrator', 'ui/ux',
    'project management', 'leadership', 'communication', 'teamwork',
]

# Education keywords
EDUCATION_KEYWORDS = [
    'bachelor', 'master', 'phd', 'doctorate', 'mba', 'b.sc', 'm.sc', 'b.tech',
    'm.tech', 'b.e', 'm.e', 'b.a', 'm.a', 'high school', 'diploma', 'certificate',
    'associate', 'degree', 'university', 'college', 'institute', 'school',
    'graduated', 'graduation', 'gpa', 'cgpa',
]

# Experience keywords
EXPERIENCE_KEYWORDS = [
    'experience', 'worked', 'employment', 'internship', 'fellowship', 'position',
    'role', 'responsibility', 'project', 'developed', 'built', 'created',
    'managed', 'led', 'designed', 'implemented', 'maintained', 'optimized',
    'years', 'year',
]


def extract_pdf_text(file_path):
    """Extract text from PDF file with OCR fallback for scanned documents"""
    text = ""
    try:
        # First attempt: Read normal PDF text with PyPDF2
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        logger.info(f"Extracted {len(text)} characters from PDF using PyPDF2")

        # OCR fallback for scanned PDFs
        if len(text.strip()) < 100 and OCR_AVAILABLE:
            logger.info(f"OCR Processing for scanned PDF: {file_path}")
            try:
                if POPPLER_PATH:
                    images = convert_from_path(file_path, poppler_path=POPPLER_PATH)
                else:
                    images = convert_from_path(file_path)

                for image in images:
                    ocr_text = pytesseract.image_to_string(image)
                    text += ocr_text + "\n"

                logger.info(f"Extracted {len(text)} characters from PDF using OCR")
            except Exception as ocr_error:
                logger.error(f"OCR failed: {ocr_error}")

    except Exception as e:
        logger.error(f"Error reading PDF {file_path}: {e}")

    return text


def extract_docx_text(file_path):
    """Extract text from DOCX file"""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
        logger.info(f"Extracted {len(text)} characters from DOCX")
    except Exception as e:
        logger.error(f"Error reading DOCX {file_path}: {e}")

    return text


def extract_text(file_path):
    """Main text extraction function - supports PDF and DOCX"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""

    file_path_lower = file_path.lower()

    if file_path_lower.endswith(".pdf"):
        return extract_pdf_text(file_path)
    elif file_path_lower.endswith(".docx"):
        return extract_docx_text(file_path)
    elif file_path_lower.endswith(".doc"):
        # Try to handle .doc files (limited support without additional libraries)
        logger.warning(f".doc format has limited support. Attempting text extraction for: {file_path}")
        try:
            # Try as if it's a docx (sometimes works)
            return extract_docx_text(file_path)
        except:
            return ""
    elif file_path_lower.endswith((".txt", ".rtf")):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file: {e}")
            return ""
    else:
        logger.warning(f"Unsupported file format: {file_path}")
        return ""


def extract_email(text):
    """Extract email addresses from text"""
    if not text:
        return ""

    # Clean text for better extraction
    text = text.replace("mailto:", "")
    text = re.sub(r"\s*@\s*", "@", text)
    text = re.sub(r"\s*\.\s*", ".", text)

    # Email regex pattern
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, text)

    if emails:
        return emails[0]  # Return first found email
    return ""


def extract_skills(text):
    """Extract skills from CV text"""
    if not text:
        return ""

    text_lower = text.lower()
    found_skills = []

    for skill in COMMON_SKILLS:
        # Use word boundary matching
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return ", ".join(found_skills) if found_skills else ""


def extract_education(text):
    """Extract education information from CV text"""
    if not text:
        return ""

    lines = text.split('\n')
    education_lines = []

    for line in lines:
        line_lower = line.lower().strip()
        if any(keyword in line_lower for keyword in EDUCATION_KEYWORDS):
            # Clean the line
            clean_line = line.strip()
            if len(clean_line) > 10:  # Filter out very short matches
                education_lines.append(clean_line)

    return "\n".join(education_lines[:10]) if education_lines else ""


def extract_experience(text):
    """Extract work experience from CV text"""
    if not text:
        return ""

    lines = text.split('\n')
    experience_lines = []

    for line in lines:
        line_lower = line.lower().strip()
        if any(keyword in line_lower for keyword in EXPERIENCE_KEYWORDS):
            clean_line = line.strip()
            if len(clean_line) > 10:
                experience_lines.append(clean_line)

    return "\n".join(experience_lines[:15]) if experience_lines else ""


def parse_cv(file_path):
    """
    Complete CV parsing - extracts all information
    Returns dictionary with all extracted data
    """
    result = {
        'text': '',
        'email': '',
        'skills': '',
        'education': '',
        'experience': '',
        'success': False,
        'error': ''
    }

    try:
        # Extract raw text
        text = extract_text(file_path)
        result['text'] = text

        if not text.strip():
            result['error'] = 'No text could be extracted from the file'
            return result

        # Extract structured information
        result['email'] = extract_email(text)
        result['skills'] = extract_skills(text)
        result['education'] = extract_education(text)
        result['experience'] = extract_experience(text)
        result['success'] = True

        logger.info(f"CV parsed successfully - Email: {result['email']}, Skills found: {len(result['skills'].split(',')) if result['skills'] else 0}")

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"CV parsing error: {e}")

    return result
