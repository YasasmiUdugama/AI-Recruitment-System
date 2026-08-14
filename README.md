# AI Recruitment System

A comprehensive Django-based AI-powered recruitment platform that automates candidate screening, ranking, interviewing, and evaluation using advanced machine learning techniques.

## Features

### 1. CV Collection and Parsing
- Upload CVs in PDF and DOCX formats
- Automatic text extraction using PyPDF2
- OCR fallback for scanned PDFs using Tesseract
- Email, skills, education, and experience extraction

### 2. AI-Based Candidate Screening
- TF-IDF vectorization for text analysis
- Cosine similarity for CV-to-job matching
- Automatic candidate ranking and scoring

### 3. Candidate Shortlisting
- Automatic selection of top N candidates
- Configurable similarity threshold
- One-click shortlisting from ranked results

### 4. Automated Email System
- Interview invitation emails with unique access tokens
- Automated rejection and selection notifications
- HTML email templates with professional design

### 5. Automated Online Interview
- Web-based interview portal with unique tokens
- Pre-defined AI interview questions
- Text and voice-based answer submission
- 3-day expiration window for interview links

### 6. AI Interview Analysis
- Keyword-based answer evaluation
- Speech-to-text using OpenAI Whisper
- Voice analysis using Librosa (pitch, energy, confidence)
- Facial emotion detection using DeepFace and OpenCV

### 7. Final Evaluation and Notification
- Automatic overall score calculation
- HR report generation
- Status-based email notifications
- Analytics dashboard with charts

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | Django 4.2+ |
| CV Parsing | PyPDF2, python-docx, pytesseract |
| Ranking | scikit-learn (TF-IDF, Cosine Similarity) |
| Speech-to-Text | OpenAI Whisper |
| Voice Analysis | Librosa |
| Emotion Detection | DeepFace, OpenCV |
| Email | Django SMTP |
| Frontend | Bootstrap 5, Chart.js |
| Database | SQLite (default) |

## Installation

### Prerequisites
- Python 3.9+
- pip
- Virtual environment (recommended)

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils libgl1-mesa-glx
```

#### macOS
```bash
brew install tesseract poppler
```

#### Windows
- Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki
- Install Poppler from: https://github.com/oschwartz10612/poppler-windows

### Setup

1. Clone or extract the project:
```bash
cd ai_recruitment
```

2. Create and activate virtual environment:
```bash
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (optional):
```bash
# Linux/macOS
export EMAIL_HOST_USER="your-email@gmail.com"
export EMAIL_HOST_PASSWORD="your-app-password"
export TESSERACT_CMD="/usr/bin/tesseract"

# Windows
set EMAIL_HOST_USER=your-email@gmail.com
set EMAIL_HOST_PASSWORD=your-app-password
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create superuser (admin):
```bash
python manage.py createsuperuser
```

7. Run the server:
```bash
python manage.py runserver
```

8. Access the application:
- Main app: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/

## Usage Guide

### 1. Create a Job Description
1. Go to the Dashboard and click "New Job Posting"
2. Fill in the job title, description, required skills, etc.
3. Save the job

### 2. Upload Candidate CVs
1. Click "Upload CV" from the navigation
2. Fill in candidate details (name, email, phone)
3. Select the job they're applying for
4. Upload their CV (PDF or DOCX)
5. The system automatically parses and extracts information

### 3. Rank Candidates
1. Go to the job detail page
2. Click "Rank All CVs" button
3. The system uses TF-IDF + Cosine Similarity to rank candidates
4. View updated similarity scores

### 4. Shortlist Candidates
1. From the job detail page, click "Auto-Shortlist Top 10"
2. Candidates with scores above the threshold are shortlisted
3. Their status changes to "Shortlisted"

### 5. Send Interview Invitations
1. Click "Send Interview Invites" on the job page
2. The system sends personalized emails with unique interview links
3. Candidates have 3 days to complete the interview

### 6. Candidate Completes Interview
1. Candidate clicks the link in their email
2. They answer 5 AI-generated questions
3. Can type answers or record voice responses
4. System analyzes answers, voice, and emotions

### 7. View Results and Generate Reports
1. Check candidate detail pages for evaluation scores
2. Generate HR reports from job pages
3. Send final result emails to candidates
4. View analytics dashboard for insights

## Project Structure

```
ai_recruitment/
  ai_recruitment/       # Django project settings
    settings.py
    urls.py
    wsgi.py
  core/                 # Main app (models, views, templates)
    models.py           # JobDescription, Candidate, Interview, etc.
    views.py            # Dashboard, CRUD operations
    admin.py            # Admin configuration
    urls.py
  parser/               # CV Parsing module
    cv_parser.py        # PDF/DOCX text extraction, OCR
    views.py
    urls.py
  ranking/              # CV Ranking module
    ranker.py           # TF-IDF + Cosine Similarity
    views.py
    urls.py
  shortlist/            # Shortlisting module
    shortlister.py      # Top N selection logic
    views.py
    urls.py
  interview/            # AI Interview module
    interview_engine.py # Questions, evaluation logic
    views.py
    urls.py
  voice/                # Voice Analysis module
    voice_analyzer.py   # Whisper STT, Librosa analysis
    views.py
    urls.py
  emotion/              # Emotion Detection module
    emotion_detector.py # DeepFace + OpenCV
    views.py
    urls.py
  emailer/              # Email System
    email_sender.py     # SMTP email functions
    views.py
    urls.py
  templates/            # HTML templates
  static/               # CSS, JS, images
  media/                # Uploaded files
  manage.py
  requirements.txt
  README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs/<id>/stats/` | GET | Get job statistics |
| `/api/candidates/<id>/update-status/` | POST | Update candidate status |
| `/parser/parse/` | POST | Parse a CV file |
| `/ranking/rank-job/<id>/` | GET | Rank candidates for a job |
| `/shortlist/api/<id>/` | GET | Shortlist candidates |
| `/interview/questions/<type>/` | GET | Get interview questions |
| `/interview/evaluate/` | POST | Evaluate an answer |
| `/interview/save-response/` | POST | Save interview response |
| `/interview/complete/` | POST | Complete interview |
| `/voice/transcribe/` | POST | Speech-to-text |
| `/voice/analyze/` | POST | Voice analysis |
| `/emotion/analyze-image/` | POST | Image emotion detection |
| `/emotion/analyze-video/` | POST | Video emotion detection |

## Configuration

### Email Settings
Update `ai_recruitment/settings.py` or set environment variables:
```python
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

For Gmail, use an App Password: https://support.google.com/accounts/answer/185833

### AI Settings
Adjust thresholds and parameters in `ai_recruitment/settings.py`:
```python
AI_SETTINGS = {
    'TFIDF_MAX_FEATURES': 5000,
    'SIMILARITY_THRESHOLD': 0.01,
    'TOP_CANDIDATES': 10,
    'INTERVIEW_QUESTION_COUNT': 5,
    'WHISPER_MODEL': 'base',
    'EMOTION_CONFIDENCE_THRESHOLD': 0.6,
}
```

### Tesseract OCR Path
Set the path to Tesseract executable:
```python
# Windows
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Linux
TESSERACT_CMD = "/usr/bin/tesseract"

# macOS
TESSERACT_CMD = "/usr/local/bin/tesseract"
```

## Troubleshooting

### Import Errors
If you encounter import errors for optional libraries (Whisper, DeepFace, Librosa), the system will run with reduced functionality. Install the specific package:
```bash
pip install openai-whisper  # For speech-to-text
pip install librosa         # For voice analysis
pip install deepface        # For emotion detection
pip install opencv-python   # For video processing
```

### Tesseract Not Found
Make sure Tesseract OCR is installed and the path is configured correctly.

### Email Not Sending
- Check your email credentials
- For Gmail, enable "Less secure app access" or use App Passwords
- Check firewall settings for SMTP port 587

## License

This project is for educational and recruitment purposes.
