from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserAuthViewSet, ArticleViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()

# Register the ArticleViewSet with the router
# This will create the following URL patterns:
# - /articles/ (GET, POST)
# - /articles/{id}/ (GET, PUT, PATCH, DELETE)
# - /articles/my_articles/ (GET - custom action)
router.register(r'articles', ArticleViewSet, basename='article')

# URL patterns for the blog app
urlpatterns = [
    # Authentication endpoints (custom actions on UserAuthViewSet)
    path('auth/register/', UserAuthViewSet.as_view({'post': 'register'}), name='user-register'),
    path('auth/login/', UserAuthViewSet.as_view({'post': 'login'}), name='user-login'),
    
    # Include the router URLs for article operations
    # This adds all the article CRUD endpoints
    path('', include(router.urls)),
]

# The complete URL structure will be:
# POST /api/auth/register/ - User registration
# POST /api/auth/login/ - User login
# GET /api/articles/ - List published articles (paginated)
# POST /api/articles/ - Create new article (authenticated users)
# GET /api/articles/{id_or_slug}/ - Get specific article
# PUT /api/articles/{id}/ - Update article (author only)
# PATCH /api/articles/{id}/ - Partial update article (author only)
# DELETE /api/articles/{id}/ - Delete article (author only)
# GET /api/articles/my_articles/ - Get user's own articles (authenticated users)