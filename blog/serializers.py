from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Article


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    Handles user creation with password confirmation and validation.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Password must be at least 8 characters long"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirm your password"
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'password_confirm']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'help_text': 'Required. 150 characters or fewer.'}
        }
    
    def validate(self, attrs):
        """
        Validate that password and password_confirm match.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Password confirmation does not match.'
            })
        return attrs
    
    def validate_email(self, value):
        """
        Validate that email is unique.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value
    
    def create(self, validated_data):
        """
        Create a new user with encrypted password.
        """
        # Remove password_confirm from validated_data
        validated_data.pop('password_confirm')
        
        # Create user with encrypted password
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user authentication/login.
    
    Accepts username and password for token generation.
    """
    username = serializers.CharField(
        help_text="Your username"
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Your password"
    )


class ArticleListSerializer(serializers.ModelSerializer):
    """
    Serializer for article list view (read-only).
    
    Used for displaying a list of published articles with minimal data
    and calculated fields like estimated read time.
    """
    author_username = serializers.CharField(source='author.username', read_only=True)
    estimated_read_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'slug',
            'status',
            'author_username',
            'estimated_read_time',
            'created_at',
            'updated_at',
            'publish_date'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def get_estimated_read_time(self, obj):
        """
        Calculate estimated reading time for the article.
        
        Args:
            obj (Article): The article instance
            
        Returns:
            int: Estimated reading time in minutes
        """
        return obj.get_estimated_read_time()


class ArticleDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for article detail view (read-only).
    
    Used for displaying a single article with full content
    and all related information.
    """
    author_username = serializers.CharField(source='author.username', read_only=True)
    estimated_read_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'content',
            'slug',
            'status',
            'author_username',
            'estimated_read_time',
            'created_at',
            'updated_at',
            'publish_date'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'author_username']
    
    def get_estimated_read_time(self, obj):
        """
        Calculate estimated reading time for the article.
        
        Args:
            obj (Article): The article instance
            
        Returns:
            int: Estimated reading time in minutes
        """
        return obj.get_estimated_read_time()


class ArticleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new articles.
    
    Handles article creation with validation and automatic author assignment.
    """
    # Make slug read-only since it's auto-generated
    slug = serializers.SlugField(read_only=True)
    
    # Make author read-only since it's set automatically from request.user
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'content',
            'slug',
            'status',
            'author',
            'publish_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'author', 'created_at', 'updated_at']
    
    def validate_title(self, value):
        """
        Validate that title is not a placeholder.
        
        Args:
            value (str): The title to validate
            
        Returns:
            str: The validated title
            
        Raises:
            serializers.ValidationError: If title is a placeholder
        """
        placeholder_titles = ['untitled', 'new post', 'title', 'article']
        if value and value.lower().strip() in placeholder_titles:
            raise serializers.ValidationError(
                'Title cannot be a placeholder like "Untitled" or "New Post".'
            )
        return value
    
    def validate_publish_date(self, value):
        """
        Validate that publish_date is in the future.
        
        Args:
            value (datetime): The publish date to validate
            
        Returns:
            datetime: The validated publish date
            
        Raises:
            serializers.ValidationError: If date is not in the future
        """
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                'Publish date must be set to a future date.'
            )
        return value
    
    def create(self, validated_data):
        """
        Create a new article with the authenticated user as author.
        
        Args:
            validated_data (dict): Validated data from the serializer
            
        Returns:
            Article: The created article instance
        """
        # Get the current user from the request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['author'] = request.user
        
        return super().create(validated_data)


class ArticleUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing articles.
    
    Similar to create serializer but excludes fields that shouldn't be updated.
    """
    # Make certain fields read-only
    slug = serializers.SlugField(read_only=True)
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'content',
            'slug',
            'status',
            'author',
            'publish_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'author', 'created_at', 'updated_at']
    
    def validate_title(self, value):
        """
        Validate that title is not a placeholder.
        
        Args:
            value (str): The title to validate
            
        Returns:
            str: The validated title
            
        Raises:
            serializers.ValidationError: If title is a placeholder
        """
        placeholder_titles = ['untitled', 'new post', 'title', 'article']
        if value and value.lower().strip() in placeholder_titles:
            raise serializers.ValidationError(
                'Title cannot be a placeholder like "Untitled" or "New Post".'
            )
        return value
    
    def validate_publish_date(self, value):
        """
        Validate that publish_date is in the future.
        
        Args:
            value (datetime): The publish date to validate
            
        Returns:
            datetime: The validated publish date
            
        Raises:
            serializers.ValidationError: If date is not in the future
        """
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                'Publish date must be set to a future date.'
            )
        return value
    
    def update(self, instance, validated_data):
        """
        Update an existing article instance.
        
        Regenerates slug if title is changed.
        
        Args:
            instance (Article): The article instance to update
            validated_data (dict): Validated data from the serializer
            
        Returns:
            Article: The updated article instance
        """
        # Check if title is being updated
        if 'title' in validated_data and validated_data['title'] != instance.title:
            # Clear the slug so it gets regenerated from the new title
            instance.slug = ''
        
        # Update the instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Save the instance (this will trigger slug regeneration if needed)
        instance.save()
        
        return instance


class UserArticleSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying a user's own articles.
    
    Shows all articles (draft and published) belonging to the authenticated user.
    """
    author_username = serializers.CharField(source='author.username', read_only=True)
    estimated_read_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'slug',
            'status',
            'author_username',
            'estimated_read_time',
            'created_at',
            'updated_at',
            'publish_date'
        ]
        read_only_fields = ['id', 'slug', 'author_username', 'created_at', 'updated_at']
    
    def get_estimated_read_time(self, obj):
        """
        Calculate estimated reading time for the article.
        
        Args:
            obj (Article): The article instance
            
        Returns:
            int: Estimated reading time in minutes
        """
        return obj.get_estimated_read_time()