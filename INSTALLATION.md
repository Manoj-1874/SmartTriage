# Quick Installation Guide for Updated SmartTriage Dashboard

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including:
- Flask-Limiter (rate limiting)
- python-dotenv (environment variables)
- psycopg2-binary (PostgreSQL support)
- pytest ecosystem (testing)

### Step 2: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your preferred editor
# For development, the defaults work out of the box!
```

### Step 3: Initialize Database

```bash
python -c "from utils.database import DatabaseManager; from config import get_config; db = DatabaseManager(get_config()); db.init_database()"
```

Or simply run the app (database initializes automatically):

```bash
python app.py
```

### Step 4: Run Tests (Optional but Recommended)

```bash
pytest
```

### Step 5: Access Application

Open your browser and navigate to:
```
http://localhost:5000
```

---

## 📦 What's New

### New Packages Installed

| Package | Purpose | Version |
|---------|---------|---------|
| Flask-Limiter | Rate limiting / DDoS protection | 3.5.0 |
| python-dotenv | Environment variable management | 1.0.0 |
| psycopg2-binary | PostgreSQL database support | 2.9.9 |
| pytest | Testing framework | 7.4.3 |
| pytest-flask | Flask testing utilities | 1.3.0 |
| pytest-cov | Code coverage reporting | 4.1.0 |
| faker | Test data generation | 20.1.0 |
| black | Code formatting | 23.12.1 |
| flake8 | Code linting | 7.0.0 |

### New Files Created

```
SmartTriage_Dashboard/
├── .env                         # Your local configuration
├── .env.example                 # Configuration template
├── config.py                    # Configuration management
├── pytest.ini                   # Test configuration
├── FIXES_SUMMARY.md             # Detailed fix documentation
├── TESTING.md                   # Testing guide
├── utils/
│   ├── __init__.py             # Utils package
│   ├── validation.py           # Input validation
│   └── database.py             # Database abstraction
├── routes/
│   ├── __init__.py             # Blueprints package
│   ├── auth.py                 # Authentication routes
│   └── triage.py               # Triage routes
└── tests/
    ├── conftest.py             # Test fixtures
    ├── test_validation.py      # Validation tests
    └── test_routes.py          # Route tests
```

---

## ⚙️ Configuration Options

### Development (Default)

The `.env` file is pre-configured for local development:
- SQLite database (no setup required)
- Rate limiting enabled (memory storage)
- Debug mode enabled
- Email disabled (console output instead)

### Production

Update `.env` for production deployment:

```bash
# Essential Production Changes
FLASK_SECRET_KEY=your-super-secret-key-here-32-chars-min
FLASK_ENV=production
FLASK_DEBUG=False

# PostgreSQL Database
DATABASE_URL=postgresql://username:password@localhost:5432/smarttriage

# Rate Limiting (Redis recommended)
RATELIMIT_STORAGE_URL=redis://localhost:6379

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
```

---

## 🧪 Running Tests

### Basic Test Run

```bash
pytest
```

### With Coverage Report

```bash
pytest --cov=. --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Run Specific Tests

```bash
# Only validation tests
pytest tests/test_validation.py

# Only route tests
pytest tests/test_routes.py

# Only tests marked as 'unit'
pytest -m unit
```

### Run in Verbose Mode

```bash
pytest -v
```

---

## 🔧 Troubleshooting

### Error: "No module named 'dotenv'"

```bash
pip install python-dotenv
```

### Error: "No module named 'flask_limiter'"

```bash
pip install Flask-Limiter
```

### Error: "No module named 'pytest'"

```bash
pip install pytest pytest-flask pytest-cov
```

### Error: "Cannot connect to PostgreSQL"

**Solution 1:** Use SQLite for development (default)
```bash
# In .env
DATABASE_URL=sqlite:///triage.db
```

**Solution 2:** Install and start PostgreSQL
```bash
# On Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# On macOS
brew install postgresql

# Create database
createdb smarttriage
```

### Error: "Tests fail with 'fixture not found'"

Make sure you're running pytest from the project root directory:
```bash
cd /path/to/SmartTriage_Dashboard
pytest
```

### Error: "Rate limit exceeded"

For development, you can disable rate limiting:
```bash
# In .env
RATELIMIT_ENABLED=false
```

---

## 📊 Verify Installation

Run this command to verify everything is set up correctly:

```bash
python -c "
from config import get_config
from utils.validation import VitalSignsValidator
from utils.database import DatabaseManager
from flask_limiter import Limiter
print('✅ All modules imported successfully!')
print('✅ Configuration loaded:', get_config().APP_NAME)
print('✅ Installation complete!')
"
```

You should see:
```
✅ All modules imported successfully!
✅ Configuration loaded: PriorityMed
✅ Installation complete!
```

---

## 🔄 Upgrading from Old Version

If you're upgrading from the previous version:

1. **Backup your database**
   ```bash
   cp triage.db triage.db.backup
   ```

2. **Install new dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create .env file**
   ```bash
   cp .env.example .env
   ```

4. **Run database migration** (automatic on first run)
   ```bash
   python app.py
   ```

5. **Run tests to verify**
   ```bash
   pytest
   ```

---

## 📝 Next Steps

1. **Review environment configuration** in `.env`
2. **Run the test suite** to ensure everything works
3. **Read TESTING.md** for comprehensive testing guide
4. **Read FIXES_SUMMARY.md** for detailed security improvements
5. **Start the application** and test the new validation!

---

## 🆘 Need Help?

- **Configuration issues:** Check `.env.example` for all options
- **Testing issues:** Read `TESTING.md`
- **Database issues:** Check `utils/database.py` comments
- **Validation errors:** See validation ranges in `utils/validation.py`

---

**Last Updated:** March 7, 2026
**Version:** 2.0 (Security & Architecture Update)
