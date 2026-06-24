# Production Deployment Recommendations
====================================

## Email System Setup

### 1. Environment Variables (.env)

Create a `.env` file in the project root (DO NOT commit this to version control):

```
env
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=ExpenseWise <your-email@gmail.com>
SITE_URL=https://yourdomain.com

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
EMAIL_RATE_LIMIT_SECONDS=300
```

### 2. Gmail App Password Setup

1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Go to App Passwords (https://myaccount.google.com/apppasswords)
4. Create a new app password for "Mail"
5. Use this 16-character password in EMAIL_HOST_PASSWORD

### 3. Required Packages

```
bash
pip install python-dotenv celery redis
```

### 4. Start Services

```
bash
# Start Redis (if not running as service)
redis-server

# Start Celery worker
celery -A expensetracker worker -l info

# Start Celery beat (for scheduled tasks)
celery -A expensetracker beat -l info
```

## Security Checklist

- [ ] Never commit credentials to version control
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS in production
- [ ] Set DEBUG=False in production
- [ ] Configure ALLOWED_HOSTS
- [ ] Use strong SECRET_KEY
- [ ] Enable CSRF protection
- [ ] Use secure session cookies

## Email Sending Events

The system sends emails for:
- ✅ Daily limit exceeded
- ✅ Goal achieved
- ✅ Suspicious login
- ✅ Password changed
- ✅ Large unusual transaction

The system does NOT send emails for:
- ❌ Expense add/edit/delete
- ❌ Search
- ❌ Voice errors
- ❌ Normal activity

## Testing Emails

```
python
# Test email configuration
from expenses.email_service import test_email_configuration

result = test_email_configuration()
print(result)
```

## Monitoring

- Check Celery logs for email delivery status
- Django logs capture email attempts in expenses.email_service logger
- Use Sentry or similar for error tracking
