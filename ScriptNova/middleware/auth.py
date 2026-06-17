from django.utils.deprecation import MiddlewareMixin
from ScriptNova.models import User
from rest_framework.response import Response
from rest_framework import status
from functools import wraps
# ScriptNova/middleware/auth.py
class AuthenticationMiddleware(MiddlewareMixin):
    EXEMPT_URLS = [
        '/api/signup/',
        '/api/login/',
        '/admin',
    ]

    def process_request(self, request):
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token = None

        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header.strip()

        # ⚡ Strip single or double quotes if present
        if token:
            token = token.strip('"').strip("'")

        request.auth_user = None

        if token:
            print(f"Checking token: {token}")  # Debug log
            try:
                user = User.objects.get(token=token)
                request.auth_user = user
                print(f"Found user: {user}")  # Debug log
            except User.DoesNotExist:
                print("User not found")  # Debug log

        return None

def require_token(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if not getattr(request, 'auth_user', None):
            return Response(
                {'success': False, 'message': 'Unauthorized', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return view_func(self, request, *args, **kwargs)
    return wrapper