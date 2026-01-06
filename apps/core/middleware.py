"""
Core middleware for security features.
"""
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
import time


class SessionTimeoutMiddleware:
    """
    Middleware de timeout de session.
    Déconnecte automatiquement un utilisateur après une période d'inactivité.
    
    Configuration via settings:
    - SESSION_TIMEOUT_MINUTES: durée d'inactivité avant déconnexion (défaut: 30)
    - SESSION_TIMEOUT_EXCLUDED_PATHS: liste de chemins exclus du reset de timeout
    
    Requirements: 6.1, 6.2, 6.3, 6.4
    """
    
    SESSION_LAST_ACTIVITY_KEY = '_session_last_activity'
    SESSION_EXPIRED_FLAG = '_session_expired'
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_minutes = getattr(settings, 'SESSION_TIMEOUT_MINUTES', 30)
        self.excluded_paths = getattr(settings, 'SESSION_TIMEOUT_EXCLUDED_PATHS', [])
    
    def __call__(self, request):
        # Only check for authenticated users
        if request.user.is_authenticated:
            # Check if current path is excluded
            if not self._is_excluded_path(request.path):
                # Check for session timeout
                if self._is_session_expired(request):
                    return self._handle_session_expired(request)
                
                # Update last activity timestamp
                self._update_last_activity(request)
        
        response = self.get_response(request)
        return response
    
    def _is_excluded_path(self, path):
        """Check if the path is excluded from timeout tracking."""
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False
    
    def _is_session_expired(self, request):
        """Check if the session has expired due to inactivity."""
        last_activity = request.session.get(self.SESSION_LAST_ACTIVITY_KEY)
        
        if last_activity is None:
            # First request, no timeout check needed
            return False
        
        # Calculate time since last activity
        try:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            if timezone.is_naive(last_activity_time):
                last_activity_time = timezone.make_aware(last_activity_time)
            
            elapsed = timezone.now() - last_activity_time
            timeout_seconds = self.timeout_minutes * 60
            
            return elapsed.total_seconds() > timeout_seconds
        except (ValueError, TypeError):
            # Invalid timestamp, reset it
            return False
    
    def _update_last_activity(self, request):
        """Update the last activity timestamp in the session."""
        request.session[self.SESSION_LAST_ACTIVITY_KEY] = timezone.now().isoformat()
    
    def _handle_session_expired(self, request):
        """Handle an expired session by logging out and redirecting."""
        # Store the expired flag before logout (session will be cleared)
        # We'll use a different approach - add message before logout
        messages.info(
            request,
            "Votre session a expiré en raison d'inactivité. Veuillez vous reconnecter."
        )
        
        # Log the session expiration in audit log
        self._log_session_expired(request)
        
        # Logout the user
        logout(request)
        
        # Redirect to login page
        login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/')
        return redirect(login_url)
    
    def _log_session_expired(self, request):
        """Log the session expiration in the audit log."""
        try:
            from apps.core.models import AuditLog
            
            # Get client IP
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.LOGOUT,
                ip_address=ip_address,
                user_agent=user_agent,
                path=request.path,
                extra_data={'reason': 'session_timeout'}
            )
        except Exception:
            # Don't let audit logging failure break the middleware
            pass
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitMiddleware:
    """
    Middleware de rate limiting.
    Limite le nombre de requêtes par utilisateur/IP pour protéger contre les abus.
    
    Configuration via settings:
    - RATE_LIMIT_ENABLED: activer/désactiver le rate limiting (défaut: True)
    - RATE_LIMIT_REQUESTS: nombre de requêtes autorisées (défaut: 100)
    - RATE_LIMIT_WINDOW: fenêtre de temps en secondes (défaut: 60)
    - RATE_LIMIT_EXCLUDED_PATHS: liste de chemins exclus du rate limiting
    
    Requirements: 9.1, 9.2, 9.3, 9.4
    """
    
    CACHE_PREFIX = 'ratelimit'
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        self.max_requests = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        self.window_seconds = getattr(settings, 'RATE_LIMIT_WINDOW', 60)
        self.excluded_paths = getattr(settings, 'RATE_LIMIT_EXCLUDED_PATHS', [
            '/static/',
            '/media/',
            '/admin/jsi18n/',
        ])
    
    def __call__(self, request):
        # Check if rate limiting is enabled (read dynamically to support testing)
        enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        if not enabled:
            return self.get_response(request)
        
        # Check if path is excluded
        if self._is_excluded_path(request.path):
            return self.get_response(request)
        
        # Check if user is admin (admins are excluded from strict limits)
        if self._is_admin_user(request):
            return self.get_response(request)
        
        # Get the rate limit key (based on user or IP)
        rate_key = self._get_rate_key(request)
        
        # Check rate limit
        if self._is_rate_limited(rate_key):
            return self._rate_limit_response(request, rate_key)
        
        # Increment request count
        self._increment_request_count(rate_key)
        
        return self.get_response(request)
    
    def _is_excluded_path(self, path):
        """Check if the path is excluded from rate limiting."""
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False
    
    def _is_admin_user(self, request):
        """
        Check if the user is an admin (excluded from strict rate limits).
        Admins have higher limits or no limits.
        """
        if not request.user.is_authenticated:
            return False
        
        # Check if user is superuser or has admin role
        if request.user.is_superuser:
            return True
        
        # Check for admin role
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True
        
        return False
    
    def _get_rate_key(self, request):
        """
        Get the cache key for rate limiting.
        Uses user ID for authenticated users, IP for anonymous.
        """
        if request.user.is_authenticated:
            identifier = f"user_{request.user.id}"
        else:
            identifier = f"ip_{self._get_client_ip(request)}"
        
        return f"{self.CACHE_PREFIX}:{identifier}"
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def _is_rate_limited(self, rate_key):
        """Check if the rate limit has been exceeded."""
        data = cache.get(rate_key)
        if data is None:
            return False
        
        request_count = data.get('count', 0)
        return request_count >= self.max_requests
    
    def _increment_request_count(self, rate_key):
        """Increment the request count for the given key."""
        data = cache.get(rate_key)
        current_time = time.time()
        
        if data is None:
            # First request in this window
            cache.set(rate_key, {
                'count': 1,
                'window_start': current_time
            }, timeout=self.window_seconds)
        else:
            window_start = data.get('window_start', current_time)
            
            # Check if we're still in the same window
            if current_time - window_start < self.window_seconds:
                # Same window, increment count
                data['count'] = data.get('count', 0) + 1
                remaining_time = self.window_seconds - (current_time - window_start)
                cache.set(rate_key, data, timeout=int(remaining_time) + 1)
            else:
                # New window, reset count
                cache.set(rate_key, {
                    'count': 1,
                    'window_start': current_time
                }, timeout=self.window_seconds)
    
    def _get_retry_after(self, rate_key):
        """Calculate the Retry-After value in seconds."""
        data = cache.get(rate_key)
        if data is None:
            return self.window_seconds
        
        window_start = data.get('window_start', time.time())
        elapsed = time.time() - window_start
        retry_after = max(1, int(self.window_seconds - elapsed))
        return retry_after
    
    def _rate_limit_response(self, request, rate_key):
        """Return a 429 Too Many Requests response."""
        retry_after = self._get_retry_after(rate_key)
        
        # Log the rate limit event
        self._log_rate_limit(request)
        
        # Check if it's an AJAX/API request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           request.content_type == 'application/json' or \
           request.path.startswith('/api/'):
            response = JsonResponse({
                'error': 'Trop de requêtes. Veuillez réessayer plus tard.',
                'retry_after': retry_after
            }, status=429)
        else:
            # For regular requests, return a simple HTML response
            from django.http import HttpResponse
            response = HttpResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>429 - Trop de requêtes</title>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        h1 {{ color: #dc3545; }}
                        p {{ color: #666; }}
                    </style>
                </head>
                <body>
                    <h1>429 - Trop de requêtes</h1>
                    <p>Vous avez effectué trop de requêtes. Veuillez réessayer dans {retry_after} secondes.</p>
                    <p><a href="javascript:history.back()">Retour</a></p>
                </body>
                </html>
                """,
                status=429,
                content_type='text/html'
            )
        
        # Add Retry-After header
        response['Retry-After'] = str(retry_after)
        return response
    
    def _log_rate_limit(self, request):
        """Log the rate limit event in the audit log."""
        try:
            from apps.core.models import AuditLog
            
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=AuditLog.Action.ACCESS_DENIED,
                ip_address=ip_address,
                user_agent=user_agent,
                path=request.path,
                extra_data={'reason': 'rate_limit_exceeded'}
            )
        except Exception:
            # Don't let audit logging failure break the middleware
            pass
