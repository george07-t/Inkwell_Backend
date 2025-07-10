from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
import re

class Article(models.Model):
    """
    Article model for the Inkwell blogging platform.
    
    This model represents a blog article with all necessary fields for
    content management, publishing workflow, and URL generation.
    """
    
    # Status choices for article publishing workflow
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    
    # Core content fields
    title = models.CharField(
        max_length=200,
        help_text="The title of the article (max 200 characters)"
    )
    
    content = models.TextField(
        help_text="The main content/body of the article"
    )
    
    # URL-friendly version of the title
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text="URL-friendly version of the title (auto-generated)"
    )
    
    # Article status for publishing workflow
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current status of the article"
    )
    
    # Relationship to the User model (author of the article)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='articles',
        help_text="The user who created this article"
    )
    
    # Optional future publishing date
    publish_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional future date when the article should be published"
    )
    
    # Automatic timestamp fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the article was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the article was last updated"
    )
    
    class Meta:
        """
        Meta options for the Article model.
        """
        # Order articles by creation date (newest first)
        ordering = ['-created_at']
        
        # Database indexes for better query performance
        indexes = [
            models.Index(fields=['status', '-created_at']),  # For published articles list
            models.Index(fields=['author', 'status']),       # For author's articles
            models.Index(fields=['slug']),                   # For slug lookups
        ]
        
        # Verbose names for admin interface
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
    
    def __str__(self):
        """
        String representation of the Article model.
        Returns the article title.
        """
        return self.title
    
    def clean(self):
        """
        Custom validation method called during model validation.

        Validates:
        1. Title is not a placeholder
        2. Publish date is in the future (if provided and status is draft)
        """
        # Validate title is not a placeholder
        placeholder_titles = ['untitled', 'new post', 'title', 'article']
        if self.title and self.title.lower().strip() in placeholder_titles:
            raise ValidationError({
                'title': 'Title cannot be a placeholder like "Untitled" or "New Post".'
            })

        # Only require future publish_date if status is draft
        if self.status == 'draft' and self.publish_date and self.publish_date <= timezone.now():
            raise ValidationError({
                'publish_date': 'Publish date must be set to a future date.'
            })    
    def save(self, *args, **kwargs):
        """
        Override the save method to automatically generate slug from title.
        
        The slug is generated from the title and made unique by appending
        a number if a duplicate exists.
        """
        if not self.slug:
            self.slug = self.generate_unique_slug()
        
        # Call the model's clean method for validation
        self.full_clean()
        
        # Call the parent save method
        super().save(*args, **kwargs)
    
    def generate_unique_slug(self):
        """
        Generate a unique slug from the article title.
        
        If a slug already exists, append a number to make it unique.
        
        Returns:
            str: A unique slug for the article
        """
        if not self.title:
            return 'article'
        
        # Create base slug from title
        base_slug = slugify(self.title)
        
        # Ensure slug is not empty
        if not base_slug:
            base_slug = 'article'
        
        # Limit slug length to prevent database issues
        base_slug = base_slug[:200]
        
        # Check if this exact slug exists
        unique_slug = base_slug
        counter = 1
        
        # Keep checking until we find a unique slug
        while Article.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
            unique_slug = f"{base_slug}-{counter}"
            counter += 1
            
            # Prevent infinite loop by limiting attempts
            if counter > 1000:
                # Fallback to timestamp-based slug
                import time
                unique_slug = f"{base_slug}-{int(time.time())}"
                break
        
        return unique_slug
    
    def get_estimated_read_time(self):
        """
        Calculate estimated reading time based on content word count.
        
        Assumes average reading speed of 200 words per minute.
        
        Returns:
            int: Estimated reading time in minutes (minimum 1 minute)
        """
        if not self.content:
            return 1
        
        # Count words in content (simple word count)
        word_count = len(re.findall(r'\b\w+\b', self.content))
        
        # Calculate reading time (200 words per minute)
        read_time = max(1, round(word_count / 200))
        
        return read_time
    
    @property
    def is_published(self):
        """
        Property to check if the article is published.
        
        Returns:
            bool: True if article status is 'published'
        """
        return self.status == 'published'
    
    @property
    def author_username(self):
        """
        Property to get the author's username.
        
        Returns:
            str: Username of the article's author
        """
        return self.author.username if self.author else None
    
    def get_absolute_url(self):
        """
        Get the absolute URL for this article.
        
        Returns:
            str: URL path for this article
        """
        return f"/articles/{self.slug}/"