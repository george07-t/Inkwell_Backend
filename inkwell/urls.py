"""inkwell URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    """
    API root endpoint that provides information about available endpoints.
    
    Returns:
        JsonResponse: Information about the API and available endpoints
    """
    return JsonResponse({
        'message': 'Welcome to Inkwell API',
        'version': '1.0',
        'endpoints': {
            'authentication': {
                'register': '/api/auth/register/',
                'login': '/api/auth/login/',
            },
            'articles': {
                'list_published': '/api/articles/',
                'create': '/api/articles/',
                'detail': '/api/articles/{id_or_slug}/',
                'update': '/api/articles/{id}/',
                'delete': '/api/articles/{id}/',
                'my_articles': '/api/articles/my_articles/',
            }
        },
        'authentication': 'Token-based authentication required for write operations',
        'documentation': 'Include Authorization header: Token <your-token-here>'
    })

urlpatterns = [
    # Django admin interface
    path('admin/', admin.site.urls),
    
    # API root endpoint
    path('api/', api_root, name='api-root'),
    
    # Blog app URLs - all blog-related endpoints under /api/
    path('api/', include('blog.urls')),
    
    # DRF browsable API authentication (for development)
    path('api-auth/', include('rest_framework.urls')),
]

# Optional: Add custom error handlers
def custom_404(request, exception):
    """Custom 404 handler for API endpoints."""
    return JsonResponse({
        'error': 'Endpoint not found',
        'message': 'The requested API endpoint does not exist.',
        'available_endpoints': '/api/'
    }, status=404)

def custom_500(request):
    """Custom 500 handler for API endpoints."""
    return JsonResponse({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end. Please try again later.'
    }, status=500)

# Set custom error handlers
handler404 = custom_404
handler500 = custom_500