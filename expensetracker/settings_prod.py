"""
Production Settings
==================
Django settings for production deployment.
Import from base.py and override for production.
"""

from .settings import *  # noqa: F401, F403

# Override debug for production
import os

DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

# Security settings (only enforce SSL redirect if not in debug mode/local testing)
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Allow loading secret key from environment
SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)

# Allowed hosts - configure for production
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'https://*.railway.app,https://*.up.railway.app,http://localhost:8000,http://127.0.0.1:8000'
).split(',')

# Database - use environment variables for Railway / production
DB_ENGINE = os.getenv('DATABASE_ENGINE', 'django.db.backends.mysql')
DB_NAME = os.getenv('MYSQLDATABASE', os.getenv('DATABASE_NAME', 'expensetracker_db'))
DB_USER = os.getenv('MYSQLUSER', os.getenv('DATABASE_USER', 'root'))
DB_PASSWORD = os.getenv('MYSQLPASSWORD', os.getenv('DATABASE_PASSWORD', ''))
DB_HOST = os.getenv('MYSQLHOST', os.getenv('DATABASE_HOST', '127.0.0.1'))
DB_PORT = os.getenv('MYSQLPORT', os.getenv('DATABASE_PORT', '3306'))

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}


# Cache - Use Redis in production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'expense_tracker',
        'TIMEOUT': 300,
    }
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Email - Use environment variables
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@yourdomain.com')

# Static files configuration (using WhiteNoise)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Inject WhiteNoise middleware right after SecurityMiddleware
if 'django.middleware.security.SecurityMiddleware' in MIDDLEWARE:
    idx = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
    MIDDLEWARE.insert(idx + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')
else:
    MIDDLEWARE.insert(0, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Insert runserver_nostatic to INSTALLED_APPS for better control in dev if needed
if 'whitenoise.runserver_nostatic' not in INSTALLED_APPS:
    INSTALLED_APPS.insert(0, 'whitenoise.runserver_nostatic')

# Optimize static files storage with compression and caching
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Logging - More verbose for production, output to console for container output capture
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'services': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# File upload size limit (10MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
