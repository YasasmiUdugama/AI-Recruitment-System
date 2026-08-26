

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


1. Create and activate virtual environment:
```bash
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:
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



