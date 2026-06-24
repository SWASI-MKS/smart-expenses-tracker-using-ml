"""
Audit Logging Middleware for tracking user actions
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from django.utils import timezone
import json

logger = logging.getLogger('audit')


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to log all significant user actions for security auditing.
    """
    
    # Paths to ignore (static files, media, etc.)
    IGNORE_PATHS = [
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon.ico',
    ]
    
    # Actions that should be logged
    LOGGED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_request(self, request):
        # Skip logging for ignored paths
        for path in self.IGNORE_PATHS:
            if path in request.path:
                return None
        
        # Store request start time
        request._audit_start_time = timezone.now()
        
        return None
    
    def process_response(self, request, response):
        # Skip if we should ignore this path
        for path in self.IGNORE_PATHS:
            if path in request.path:
                return response
        
        # Only log for authenticated users on sensitive actions
        if not request.user.is_authenticated:
            return response
        
        # Log POST, PUT, PATCH, DELETE requests
        if request.method in self.LOGGED_METHODS:
            self._log_action(request, response)
        
        return response
    
    def _log_action(self, request, response):
        """Log the action details"""
        try:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            
            # Determine action type
            action = self._get_action_type(request)
            
            # Get additional details
            details = {
                'method': request.method,
                'path': request.path,
                'ip': ip,
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200],
            }
            
            # Add request body for POST/PUT/PATCH (excluding passwords)
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = request.POST.dict().copy()
                    # Exclude sensitive fields
                    sensitive_fields = ['password', 'csrfmiddlewaretoken', 'card_number', 'cvv']
                    for field in sensitive_fields:
                        if field in body:
                            body[field] = '***REDACTED***'
                    details['body'] = body
                except:
                    pass
            
            # Add response status
            details['status_code'] = response.status_code
            
            # Log the action
            log_message = f"AUDIT: User '{request.user.username}' performed '{action}' on '{request.path}' - Status: {response.status_code}"
            
            if response.status_code >= 400:
                logger.warning(log_message, extra=details)
            else:
                logger.info(log_message, extra=details)
                
        except Exception as e:
            logger.error(f"Error in audit middleware: {str(e)}")
    
    def _get_action_type(self, request):
        """Determine the action type based on URL and method"""
        path = request.path.lower()
        
        if '/add' in path or '/create' in path:
            return 'CREATE'
        elif '/edit' in path or '/update' in path or '/patch' in request.method.lower():
            return 'UPDATE'
        elif '/delete' in path or '/remove' in path:
            return 'DELETE'
        elif '/login' in path:
            return 'LOGIN'
        elif '/logout' in path:
            return 'LOGOUT'
        else:
            return request.method


class AccountLockoutMiddleware(MiddlewareMixin):
    """
    Middleware to handle account lockout after failed login attempts.
    """
    
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 15  # minutes
    
    def process_request(self, request):
        # Only check on login POST
        if request.path != '/authentication/login/' or request.method != 'POST':
            return None
        
        username = request.POST.get('username')
        if not username:
            return None
        
        # Check if user exists and is locked
        from django.core.cache import cache
        cache_key = f'failed_login_{username}'
        failed_attempts = cache.get(cache_key, 0)
        
        if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            # Check if lockout has expired
            lockout_key = f'lockout_{username}'
            lockout_time = cache.get(lockout_key)
            
            if lockout_time:
                from django.utils import timezone
                lockout_expires = lockout_time + timezone.timedelta(minutes=self.LOCKOUT_DURATION)
                
                if timezone.now() < lockout_expires:
                    # User is still locked
                    request.session['lockout_message'] = (
                        f"Account temporarily locked due to too many failed login attempts. "
                        f"Try again after {self.LOCKOUT_DURATION} minutes."
                    )
                else:
                    # Lockout expired, reset
                    cache.delete(cache_key)
                    cache.delete(lockout_key)
        
        return None
