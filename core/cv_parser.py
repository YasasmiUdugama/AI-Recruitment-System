import os
import re
import logging

# PDF handling
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# DOCX handling
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# OCR fallback
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False



logger = logging.getLogger('ai_recruitment')

# Configure Tesseract path (update based on your system)
TESSERACT_CMD = os.environ.get(
    'TESSERACT_CMD',
    r'D:\HR Recruitment System\Tesseract\tesseract.exe'
)
if OCR_AVAILABLE:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
POPPLER_PATH = os.environ.get(
    'POPPLER_PATH',
    r'D:\HR Recruitment System\poppler-26.02.0\Library\bin'
)
print(f"DEBUG STARTUP: PYPDF2_AVAILABLE={PYPDF2_AVAILABLE}, OCR_AVAILABLE={OCR_AVAILABLE}, TESSERACT_CMD={TESSERACT_CMD}, POPPLER_PATH={POPPLER_PATH}")

# Valid TLDs for email cleanup
VALID_TLDS = {
    'com', 'org', 'net', 'edu', 'gov', 'mil', 'int', 'co', 'io', 'ai',
    'uk', 'us', 'ca', 'au', 'de', 'fr', 'jp', 'cn', 'in', 'lk', 'sg',
    'info', 'biz', 'name', 'pro', 'aero', 'jobs', 'mobi', 'travel',
    'app', 'dev', 'cloud', 'tech', 'online', 'store', 'blog',
}

# Common skills dictionary for extraction
COMMON_SKILLS = [
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'swift',
    'kotlin', 'ruby', 'php', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash',
    'html', 'css', 'react', 'angular', 'vue', 'nodejs', 'django', 'flask', 'spring',
    'express', 'next.js', 'nuxt', 'bootstrap', 'tailwind', 'jquery',
    'sql', 'mysql', 'postgresql', 'mongodb', 'sqlite', 'redis', 'elasticsearch',
    'cassandra', 'dynamodb', 'firebase', 'oracle', 'mariadb',
    'pandas', 'numpy', 'scipy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras',
    'matplotlib', 'seaborn', 'plotly', 'power bi', 'tableau', 'machine learning',
    'deep learning', 'nlp', 'computer vision', 'data analysis', 'data visualization',
    'statistics', 'jupyter', 'anaconda', 'opencv',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'github',
    'gitlab', 'terraform', 'ansible', 'nginx', 'apache', 'linux', 'ci/cd',
    'android', 'ios', 'flutter', 'react native', 'xamarin', 'ionic',
    'rest api', 'graphql', 'json', 'xml', 'soap', 'microservices', 'agile', 'scrum',
    'jira', 'confluence', 'figma', 'photoshop', 'illustrator', 'ui/ux',
    'project management', 'leadership', 'communication', 'teamwork',
]

EDUCATION_KEYWORDS = [
    'bachelor', 'master', 'phd', 'doctorate', 'mba', 'b.sc', 'm.sc', 'b.tech',
    'm.tech', 'b.e', 'm.e', 'b.a', 'm.a', 'high school', 'diploma', 'certificate',
    'associate', 'degree', 'university', 'college', 'institute', 'school',
    'graduated', 'graduation', 'gpa', 'cgpa',
]

EXPERIENCE_KEYWORDS = [
    'experience', 'worked', 'employment', 'internship', 'fellowship', 'position',
    'role', 'responsibility', 'project', 'developed', 'built', 'created',
    'managed', 'led', 'designed', 'implemented', 'maintained', 'optimized',
    'years', 'year',
]

# Words that should NEVER be part of a person's name
EXCLUDE_NAME_WORDS = {
    'resume', 'curriculum', 'vitae', 'cv', 'name', 'contact',
    'address', 'phone', 'email', 'linkedin', 'github', 'portfolio',
    'objective', 'summary', 'profile', 'education', 'experience',
    'skills', 'references', 'date', 'page', 'of', 'the', 'and', 'or',
    'to', 'in', 'for', 'with', 'on', 'at', 'from', 'by', 'about',
    'present', 'current', 'january', 'february', 'march', 'april',
    'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
    'street', 'avenue', 'road', 'lane', 'drive', 'blvd', 'city', 'state',
    'zip', 'postal', 'area', 'code', 'mobile', 'tel', 'fax', 'www',
    'http', 'https', 'com', 'org', 'net', 'edu', 'gov', 'inc', 'ltd',
    'software', 'engineer', 'developer', 'manager', 'analyst', 'consultant',
    'senior', 'junior', 'lead', 'principal', 'associate', 'executive',
    'professional', 'precis', 'about', 'me', 'personal', 'details',
    'declaration', 'activities', 'achievements', 'awards', 'certificates',
    'referees', 'references', 'trainings', 'projects', 'areas', 'expertise',
    'independent', 'consultant', 'factory', 'accountant', 'assistant',
    'chief', 'operating', 'officer', 'deputy', 'general', 'manager',
    'principle', 'software', 'colonel', 'member', 'member-', 'sri', 'lanka',
    'university', 'college', 'school', 'department', 'group', 'limited',
    'phone', 'email', 'tel', 'fax', 'linkedin', 'skype',
    # Section headers that appear as capitalized words
    'eminent', 'feats', 'qualifications', 'affiliations', 'professional',
    'independent', 'consultant', 'manager', 'process', 'compliance',
    'factory', 'accountant', 'assistant', 'accountant', 'trainings',
    'referees', 'areas', 'expertise', 'projects', 'skills', 'soft',
    'certificates', 'certficates', 'achievements', 'awards', 'activities',
    'personal', 'details', 'declaration', 'references', 'about',
}

# Non-personal email patterns to exclude
EXCLUDE_EMAIL_PATTERNS = [
    'info@', 'support@', 'contact@', 'admin@', 'sales@', 'marketing@',
    'noreply@', 'no-reply@', 'help@', 'careers@', 'jobs@', 'hr@',
    'recruit@', 'enquiries@', 'inquiries@', 'webmaster@', 'postmaster@',
    'abuse@', 'security@', 'billing@', 'accounts@', 'feedback@',
    'service@', 'services@', 'team@', 'hello@', 'press@', 'media@',
]


def extract_pdf_text(file_path):
    """Extract text from PDF file with OCR fallback for scanned documents"""
    text = ""
    if not PYPDF2_AVAILABLE:
        logger.warning("PyPDF2 not available")
        return text

    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.error(f"PyPDF2 read failed: {e}")

    logger.info(f"After PyPDF2: {len(text.strip())} chars, OCR_AVAILABLE={OCR_AVAILABLE}, len<100={len(text.strip()) < 100}")

    if len(text.strip()) < 100 and OCR_AVAILABLE:
        try:
            if POPPLER_PATH:
                images = convert_from_path(file_path, poppler_path=POPPLER_PATH)
            else:
                images = convert_from_path(file_path)
            logger.info(f"Converted to {len(images)} image(s) for OCR")
            for image in images:
                ocr_text = pytesseract.image_to_string(image)
                text += ocr_text + "\n"
            logger.info(f"After OCR: {len(text.strip())} chars")
        except Exception as ocr_error:
            logger.error(f"OCR failed: {ocr_error}", exc_info=True)
 
    return text

def extract_docx_text(file_path):
    """Extract text from DOCX file"""
    text = ""
    if not DOCX_AVAILABLE:
        return text
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        logger.error(f"Error reading DOCX {file_path}: {e}")
    return text


def extract_text(file_path):
    """Main text extraction function"""
    if not os.path.exists(file_path):
        return ""
    file_path_lower = file_path.lower()
    if file_path_lower.endswith(".pdf"):
        return extract_pdf_text(file_path)
    elif file_path_lower.endswith(".docx"):
        return extract_docx_text(file_path)
    elif file_path_lower.endswith(".doc"):
        try:
            return extract_docx_text(file_path)
        except:
            return ""
    elif file_path_lower.endswith((".txt", ".rtf")):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return ""
    return ""


def preprocess_text(text):
    """
    Preprocess extracted text to fix common PDF extraction issues:
    - Merge emails with following text (e.g., gmail.comNo -> gmail.com No)
    - Fix spaces around @
    """
    if not text:
        return text
    
    # Fix spaces around @ symbol
    text = text.replace("mailto:", "")
    text = re.sub(r"\s*@\s*", "@", text)
    
    # Fix merged emails: insert space after TLD when followed by capital letter or number
    # e.g., "gmail.comNo.82" -> "gmail.com No.82"
    text = re.sub(r'(\.[a-zA-Z]{2,6})([A-Z0-9])', r'\1 \2', text)
    
    # Also fix when followed by common punctuation patterns
    text = re.sub(r'(\.[a-zA-Z]{2,6})(No\.\d)', r'\1 \2', text)
    
    return text


def is_personal_email(email):
    """Check if email looks like a personal/candidate email (not a company generic one)"""
    email_lower = email.lower()
    for pattern in EXCLUDE_EMAIL_PATTERNS:
        if pattern in email_lower:
            return False
    local = email_lower.split('@')[0]
    if len(local) <= 2:
        return False
    return True


def clean_email(email):
    """Fix emails where TLD got merged with following text (e.g., gmail.comno -> gmail.com)"""
    email = email.lower().strip()
    parts = email.split('@')
    if len(parts) != 2:
        return email
    domain = parts[1]
    for tld in sorted(VALID_TLDS, key=len, reverse=True):
        tld_with_dot = '.' + tld
        if domain.endswith(tld_with_dot):
            return email
        idx = domain.find(tld_with_dot)
        if idx != -1:
            clean_domain = domain[:idx + len(tld_with_dot)]
            return parts[0] + '@' + clean_domain
    return email


def extract_email(text):
    """Extract the candidate's email from text. Prioritizes emails found early in the document."""
    if not text:
        return ""

    # Preprocess to fix merged text
    text = preprocess_text(text)

    # Find all emails - cap TLD at 2-6 letters, word boundary after
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b"
    all_emails = re.findall(email_pattern, text)

    if not all_emails:
        return ""

    # Deduplicate while preserving order
    seen = set()
    unique_emails = []
    for e in all_emails:
        e_clean = e.lower().strip()
        if e_clean not in seen:
            seen.add(e_clean)
            unique_emails.append(e_clean)

    # Clean emails (fix merged TLDs) and filter out placeholders
    cleaned_emails = []
    for email in unique_emails:
        email = clean_email(email)
        if any(x in email for x in ['example.com', 'test.com', 'domain.com', 'yourdomain.com']):
            continue
        cleaned_emails.append(email)

    if not cleaned_emails:
        return ""

    # Strategy 1: Find first personal email in the first 1500 chars (header/contact area)
    header_text = text[:1500].lower()
    for email in cleaned_emails:
        if email in header_text and is_personal_email(email):
            return email

    # Strategy 2: Return first valid personal email anywhere
    for email in cleaned_emails:
        if is_personal_email(email):
            return email

    # Strategy 3: Fallback to first valid email
    return cleaned_emails[0]


def looks_like_name(words):
    """Check if a list of words looks like a person's name"""
    if not (2 <= len(words) <= 4):
        return False
    
    # All must be alphabetic and >1 char
    if not all(w.isalpha() and len(w) > 1 for w in words):
        return False
    
    # No excluded words
    if any(w.lower() in EXCLUDE_NAME_WORDS for w in words):
        return False
    
    # Reasonable total length
    total_len = sum(len(w) for w in words)
    if not (6 <= total_len <= 40):
        return False
    
    # Must be title case (First letter uppercase, rest lowercase-ish)
    # OR all uppercase (will convert later)
    all_title_case = all(w[0].isupper() for w in words)
    all_upper = all(w.isupper() for w in words)
    
    if not (all_title_case or all_upper):
        return False
    
    # Additional: reject if it looks like a job title
    title_indicators = ['engineer', 'developer', 'manager', 'analyst', 'consultant',
                        'director', 'coordinator', 'specialist', 'administrator',
                        'architect', 'designer', 'executive', 'officer', 'president',
                        'vice', 'vp', 'head', 'lead', 'chief', 'senior', 'junior',
                        'process', 'compliance', 'finance', 'quality', 'professional']
    if any(w.lower() in title_indicators for w in words):
        return False
    
    return True


def extract_name_from_text(text, email=""):
    """
    Extract candidate name from CV text.
    Returns (first_name, last_name)
    """
    if not text:
        return "", ""

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return "", ""

    # ==================================================================
    # STRATEGY 1: Explicit "Name:" or "Full Name:" labels (first 30 lines)
    # ==================================================================
    name_label_patterns = [
        r'[Nn]ame\s*[:\-]\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})',
        r'[Ff]ull\s*[Nn]ame\s*[:\-]\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})',
    ]
    header_text = '\n'.join(lines[:30])
    for pattern in name_label_patterns:
        match = re.search(pattern, header_text)
        if match:
            full_name = match.group(1).strip()
            parts = full_name.split()
            filtered = [p for p in parts if p.lower() not in EXCLUDE_NAME_WORDS]
            if len(filtered) >= 2:
                return filtered[0], ' '.join(filtered[1:])
            if len(parts) >= 2:
                return parts[0], ' '.join(parts[1:])

    # ==================================================================
    # STRATEGY 2: First 3 lines - very often the candidate's name is here
    # ==================================================================
    for line_idx in range(min(3, len(lines))):
        line = lines[line_idx]
        # Clean the line - remove common prefixes
        clean_line = re.sub(r'^(?:#|\*|\-|[0-9]+\.)\s*', '', line).strip()
        words = clean_line.split()
        
        if looks_like_name(words):
            # Convert to title case if all uppercase
            if all(w.isupper() for w in words):
                words = [w.title() for w in words]
            return words[0], ' '.join(words[1:])

    # ==================================================================
    # STRATEGY 3: Scan first 15 lines for 2-4 capitalized words
    # ==================================================================
    for line in lines[:15]:
        if len(line) > 60 or len(line) < 4:
            continue
        # Skip lines that are clearly section headers
        if line.startswith('#') or line.startswith('*') or line.startswith('-'):
            continue
        # Skip lines with numbers, special chars, or URLs
        if re.search(r'[0-9@/:;!?&|\-]', line):
            continue

        clean_line = re.sub(r'[^\w\s]', ' ', line)
        words = clean_line.split()

        # Look for consecutive capitalized words
        for j in range(len(words)):
            candidate_words = []
            for k in range(j, min(j + 4, len(words))):
                word = words[k]
                if word and word[0].isupper() and len(word) > 1 and word.isalpha():
                    if word.lower() not in EXCLUDE_NAME_WORDS:
                        candidate_words.append(word)
                    else:
                        break
                elif candidate_words:
                    break

            if len(candidate_words) >= 2:
                full_name = ' '.join(candidate_words)
                if 5 <= len(full_name) <= 40:
                    # Reject if it contains title indicators
                    title_indicators = {'engineer', 'developer', 'manager', 'analyst', 
                                        'consultant', 'director', 'specialist', 'professional',
                                        'process', 'compliance', 'finance', 'quality'}
                    if not any(w.lower() in title_indicators for w in candidate_words):
                        return candidate_words[0], ' '.join(candidate_words[1:])

    # ==================================================================
    # STRATEGY 4: Extract from email local part
    # ==================================================================
    if email and '@' in email:
        local = email.split('@')[0]
        local = re.sub(r'[._\-\d]', ' ', local)
        parts = local.split()
        parts = [p.capitalize() for p in parts if len(p) > 1]
        if len(parts) >= 2:
            return parts[0], ' '.join(parts[1:])
        elif len(parts) == 1:
            return parts[0], ""
    return "", ""


def extract_skills(text):
    """Extract skills from CV text"""
    if not text:
        return ""
    text_lower = text.lower()
    found_skills = []
    for skill in COMMON_SKILLS:
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
            clean_line = line.strip()
            if len(clean_line) > 10:
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
    """Complete CV parsing - extracts all information"""
    result = {
        'text': '',
        'email': '',
        'first_name': '',
        'last_name': '',
        'skills': '',
        'education': '',
        'experience': '',
        'success': False,
        'error': ''
    }

    try:
        text = extract_text(file_path)
        result['text'] = text

        if not text.strip():
            result['error'] = 'No text could be extracted from the file'
            return result

        # Extract email first, then use it to help find name
        result['email'] = extract_email(text)
        first_name, last_name = extract_name_from_text(text, result['email'])
        result['first_name'] = first_name
        result['last_name'] = last_name
        result['skills'] = extract_skills(text)
        result['education'] = extract_education(text)
        result['experience'] = extract_experience(text)
        result['success'] = True

        logger.info(
            f"CV parsed - Name: '{first_name} {last_name}', "
            f"Email: '{result['email']}'"
        )

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"CV parsing error: {e}")

    return result