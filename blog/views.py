from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q

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
    
    Sets page size and allows clients to control page size within limits.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class UserAuthViewSet(viewsets.ViewSet):
    """
    ViewSet for user authentication operations.
    
    Provides endpoints for user registration and login.
    """
    # Set default permission to AllowAny for the entire ViewSet
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new user.
        
        Args:
            request: HTTP request containing user registration data
            
        Returns:
            Response: User data and authentication token
        """
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Create authentication token for the user
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
        """
        Authenticate a user and return a token.
        
        Args:
            request: HTTP request containing login credentials
            
        Returns:
            Response: Authentication token and user data
        """
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            # Authenticate user
            user = authenticate(username=username, password=password)
            
            if user:
                # Get or create token
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

from django.utils import timezone

def publish_scheduled_articles():
    """
    Update all draft articles whose publish_date has passed to published.
    """
    now = timezone.now()
    from .models import Article
    articles = Article.objects.filter(
        status='draft',
        publish_date__isnull=False,
        publish_date__lte=now
    )
    for article in articles:
        article.status = 'published'
        article.save()

class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for article CRUD operations.
    
    Provides endpoints for creating, reading, updating, and deleting articles.
    Includes proper permissions and efficient database queries.
    """
    
    pagination_class = ArticlePagination
    permission_classes = [IsAuthorOrReadOnly]
    
    def get_queryset(self):
        """
        Return the appropriate queryset based on the action.
        
        - For list view: only published articles
        - For detail view: published articles or user's own articles
        - For other actions: all articles (permissions will handle access)
        
        Returns:
            QuerySet: Filtered queryset with optimized database queries
        """
        publish_scheduled_articles()
        # Use select_related to avoid N+1 queries when accessing author data
        base_queryset = Article.objects.select_related('author')
        
        if self.action == 'list':
            # For list view, only show published articles
            return base_queryset.filter(status='published')
        elif self.action == 'retrieve':
            # For detail view, show published articles or user's own articles
            if self.request.user.is_authenticated:
                return base_queryset.filter(
                    Q(status='published') | Q(author=self.request.user)
                )
            else:
                return base_queryset.filter(status='published')
        else:
            # For other actions (create, update, delete), return all articles
            # Permissions will handle access control
            return base_queryset
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.
        
        Returns:
            Serializer: The serializer class to use
        """
        if self.action == 'list':
            return ArticleListSerializer
        elif self.action == 'retrieve':
            return ArticleDetailSerializer
        elif self.action == 'create':
            return ArticleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ArticleUpdateSerializer
        elif self.action == 'my_articles':
            return UserArticleSerializer
        else:
            return ArticleDetailSerializer
    
    def get_permissions(self):
        """
        Return the appropriate permission classes based on the action.
        
        Returns:
            list: List of permission class instances
        """
        if self.action in ['list', 'retrieve']:
            # For reading, use the published or author permission
            permission_classes = [IsPublishedOrAuthor]
        elif self.action == 'my_articles':
            # For user's own articles, require ownership
            permission_classes = [IsOwnerOrCreateOnly]
        else:
            # For create, update, delete operations
            permission_classes = [IsAuthorOrReadOnly]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Save the article with the current user as the author.
        
        Args:
            serializer: The serializer instance
        """
        serializer.save(author=self.request.user)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_articles(self, request):
        """
        Get all articles belonging to the authenticated user.
        
        Returns both draft and published articles of the current user.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: Paginated list of user's articles
        """
        # Get all articles by the current user (both draft and published)
        queryset = Article.objects.filter(author=request.user).select_related('author')
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserArticleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # If pagination is not configured, return all results
        serializer = UserArticleSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single article.
        
        Override to handle slug-based lookup and proper permissions.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: Article data or 404/403 error
        """
        try:
            # Try to get the article by slug first, then by pk
            lookup_value = kwargs.get('pk')
            if lookup_value.isdigit():
                article = self.get_queryset().get(pk=lookup_value)
            else:
                article = self.get_queryset().get(slug=lookup_value)
            
            # Check object permissions
            self.check_object_permissions(request, article)
            
            serializer = self.get_serializer(article)
            return Response(serializer.data)
            
        except Article.DoesNotExist:
            return Response(
                {'error': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def list(self, request, *args, **kwargs):
        """
        List all published articles.
        
        Override to add custom filtering and ensure only published articles are shown.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: Paginated list of published articles
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # If pagination is not configured, return all results
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        Update an article.
        
        Override to ensure proper permission checking and validation.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: Updated article data or error
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if user has permission to update this article
        self.check_object_permissions(request, instance)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete an article.
        
        Override to ensure proper permission checking.
        
        Args:
            request: HTTP request
            
        Returns:
            Response: Success message or error
        """
        instance = self.get_object()
        
        # Check if user has permission to delete this article
        self.check_object_permissions(request, instance)
        
        self.perform_destroy(instance)
        return Response(
            {'message': 'Article deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )