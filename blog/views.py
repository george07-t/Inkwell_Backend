from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Article
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    ArticleListSerializer,
    ArticleDetailSerializer,
    ArticleCreateSerializer,
    ArticleUpdateSerializer,
    UserArticleSerializer
)
from .permissions import IsAuthorOrReadOnly, IsOwnerOrCreateOnly, IsPublishedOrAuthor


class ArticlePagination(PageNumberPagination):
    """
    Custom pagination class for articles.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


def publish_scheduled_articles():
    """
    Update all draft articles whose publish_date has passed to published.
    """
    now = timezone.now()
    articles = Article.objects.filter(
        status='draft',
        publish_date__isnull=False,
        publish_date__lte=now
    )
    for article in articles:
        article.status = 'published'
        article.save()


class UserAuthViewSet(viewsets.ViewSet):
    """
    ViewSet for user authentication operations.
    """
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            
            if user:
                token, created = Token.objects.get_or_create(user=user)
                
                return Response({
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    },
                    'token': token.key
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid username or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PublicArticleListView(APIView):
    """
    API view for listing all published articles (public access).
    
    GET /articles/public_articles/
    """
    permission_classes = [permissions.AllowAny]
    pagination_class = ArticlePagination
    
    def get(self, request):
        """
        Return a list of all published articles.
        """
        publish_scheduled_articles()
        
        # Get all published articles
        queryset = Article.objects.filter(status='published').select_related('author')
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicArticleDetailView(APIView):
    """
    API view for retrieving a specific published article (public access).
    
    GET /articles/public_articles/<pk>/
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, pk):
        """
        Return a specific published article by pk or slug.
        """
        publish_scheduled_articles()
        
        try:
            # Try to get by pk first, then by slug
            if pk.isdigit():
                article = Article.objects.select_related('author').get(
                    pk=pk, status='published'
                )
            else:
                article = Article.objects.select_related('author').get(
                    slug=pk, status='published'
                )
            
            serializer = ArticleDetailSerializer(article)
            return Response(serializer.data)
            
        except Article.DoesNotExist:
            return Response(
                {'error': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserArticleListView(APIView):
    """
    API view for listing user's articles with permission checking.
    
    GET /articles/user_articles/<user_id>/
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ArticlePagination
    
    def get(self, request, user_id):
        """
        Return articles for a specific user.
        If it's the current user, return all articles (draft + published).
        If it's another user, return only published articles.
        """
        publish_scheduled_articles()
        
        # Get the target user
        target_user = get_object_or_404(User, id=user_id)
        
        # Check if requesting user is the same as target user
        if request.user.id == int(user_id):
            # Own articles - show all (draft + published)
            queryset = Article.objects.filter(author=target_user).select_related('author')
            serializer_class = UserArticleSerializer
        else:
            # Other user's articles - show only published
            queryset = Article.objects.filter(
                author=target_user, status='published'
            ).select_related('author')
            serializer_class = ArticleListSerializer
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = serializer_class(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = serializer_class(queryset, many=True)
        return Response(serializer.data)


class UserArticleDetailView(APIView):
    """
    API view for retrieving, updating, and deleting user's articles.
    
    GET /articles/user_articles/<user_id>/<pk>/
    PUT /articles/user_articles/<user_id>/<pk>/
    PATCH /articles/user_articles/<user_id>/<pk>/
    DELETE /articles/user_articles/<user_id>/<pk>/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_article(self, user_id, pk, request_user):
        """
        Get article with proper permission checking.
        """
        target_user = get_object_or_404(User, id=user_id)
        
        try:
            if pk.isdigit():
                article = Article.objects.select_related('author').get(
                    pk=pk, author=target_user
                )
            else:
                article = Article.objects.select_related('author').get(
                    slug=pk, author=target_user
                )
            
            # Permission check
            if request_user.id == int(user_id):
                # Own article - can see all
                return article
            else:
                # Other user's article - only if published
                if article.status == 'published':
                    return article
                else:
                    return None
        except Article.DoesNotExist:
            return None
    
    def get(self, request, user_id, pk):
        """
        Retrieve a specific article.
        """
        publish_scheduled_articles()
        
        article = self.get_article(user_id, pk, request.user)
        
        if not article:
            return Response(
                {'error': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use appropriate serializer based on ownership
        if request.user.id == int(user_id):
            serializer = ArticleDetailSerializer(article)
        else:
            serializer = ArticleDetailSerializer(article)
        
        return Response(serializer.data)
    
    def put(self, request, user_id, pk):
        """
        Fully update an article (only owner can update).
        """
        # Only allow owner to update
        if request.user.id != int(user_id):
            return Response(
                {'error': 'You can only edit your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        article = self.get_article(user_id, pk, request.user)
        
        if not article:
            return Response(
                {'error': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ArticleUpdateSerializer(
            article, data=request.data, context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, user_id, pk):
        """
        Partially update an article (only owner can update).
        """
        # Only allow owner to update
        if request.user.id != int(user_id):
            return Response(
                {'error': 'You can only edit your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        article = self.get_article(user_id, pk, request.user)
        
        if not article:
            return Response(
                {'error': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ArticleUpdateSerializer(
            article, data=request.data, partial=True, context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, user_id, pk):
        """
        Delete an article (only owner can delete).
        """
        # Only allow owner to delete
        if request.user.id != int(user_id):
            return Response(
                {'error': 'You can only delete your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        article = self.get_article(user_id, pk, request.user)
        
        if not article:
            return Response(
                {'error': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        article.delete()
        return Response(
            {'message': 'Article deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )

class CreateArticleView(APIView):
    """
    API view for creating new articles.
    
    POST /articles/create/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Create a new article.
        """
        serializer = ArticleCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            article = serializer.save(author=request.user)
            return Response(
                ArticleDetailSerializer(article).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)