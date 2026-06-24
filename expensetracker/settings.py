from pathlib import Path
from django.contrib import messages
import os
import matplotlib
matplotlib.use('Agg')
import pymysql
pymysql.install_as_MySQLdb()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-#e(g$@-wfcc07s^4avvl4ls)fx1uo-3p=gp9ol5w5g(!0k*0r4'
DEBUG = True
ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'expenses',
    'authentication',
    'userpreferences',
    'userincome',
    'expense_forecast',
    'rest_framework',
    'api',
    'goals',
    'userprofile',
    'bank_simulator',
    'report_generation',
    'notifications',
    'debts',  
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware for security
    'auditmiddleware.middleware.AuditMiddleware',
]
ROOT_URLCONF = 'expensetracker.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Global currency context processor
                'userpreferences.context_processors.currency_context',
                # Goals summary context processor
                'goals.context_processors.goals_summary_processor',
                # Bank summary context processor
                'bank_simulator.context_processors.bank_summary_processor',
            ],
        },
    },
]
WSGI_APPLICATION = 'expensetracker.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'expensetracker_db',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    # Custom password validators
    {
        'NAME': 'authentication.password_validators.UppercaseValidator',
    },
    {
        'NAME': 'authentication.password_validators.SpecialCharValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

# Email Settings 
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  

# Email Backend Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')

# SMTP Configuration
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'

# SMTP Credential
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'finalyearprojectteam05@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'vpef dfcx lbwc nhqn')

# Default sender email
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'finalyearprojectteam05@gmail.com')

# Optional: Site URL for email templates
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')
EMAIL_RATE_LIMIT_SECONDS = int(os.getenv('EMAIL_RATE_LIMIT_SECONDS', 300))  # 5 minutes default
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# ================= AUTH REDIRECTS =================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'overview'
LOGOUT_REDIRECT_URL = 'home'

# Cache Configuration 
# Development: Local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes default timeout
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# Tesseract OCR configuration 
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    pass  

# Daily Summary Configuration
DAILY_SUMMARY_ENABLED = os.getenv('DAILY_SUMMARY_ENABLED', 'True').lower() == 'true'

# Batch size for processing users (100-200 to avoid email rate limits)
DAILY_SUMMARY_BATCH_SIZE = int(os.getenv('DAILY_SUMMARY_BATCH_SIZE', '100'))

# Default timezone for new users
DEFAULT_USER_TIMEZONE = os.getenv('DEFAULT_USER_TIMEZONE', 'UTC')

# Default daily summary time (HH:MM format)
DEFAULT_DAILY_SUMMARY_TIME = os.getenv('DEFAULT_DAILY_SUMMARY_TIME', '00:00')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'audit': {
            'format': '{asctime} | {levelname} | {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'audit_file': {
            'class': 'logging.FileHandler',
            'filename': 'audit.log',
            'formatter': 'audit',
        },
    },
    'loggers': {
        'services.daily_summary_service': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'notifications.tasks': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ================= SECURITY SETTINGS =================
# Account lockout settings
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_DURATION = 15  # minutes

# Session settings
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF settings - Use cookie-based CSRF 
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript to read
CSRF_USE_SESSIONS = False  # Use cookie instead of session for CSRF
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
