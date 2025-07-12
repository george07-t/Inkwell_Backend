from django.urls import path
from .views import (
    UserAuthViewSet,
    PublicArticleListView,
    PublicArticleDetailView,
    UserArticleListView,
    UserArticleDetailView,
    CreateArticleView
)

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', UserAuthViewSet.as_view({'post': 'register'}), name='user-register'),
    path('auth/login/', UserAuthViewSet.as_view({'post': 'login'}), name='user-login'),
    
    # Public article endpoints (no authentication required)
    path('articles/public_articles/', PublicArticleListView.as_view(), name='public-article-list'),
    path('articles/public_articles/<str:pk>/', PublicArticleDetailView.as_view(), name='public-article-detail'),
    
    # User article endpoints (authentication required)
    path('articles/user_articles/<int:user_id>/', UserArticleListView.as_view(), name='user-article-list'),
    path('articles/user_articles/<int:user_id>/<str:pk>/', UserArticleDetailView.as_view(), name='user-article-detail'),
    
    # Article creation endpoint
    path('articles/create/', CreateArticleView.as_view(), name='create-article'),
]