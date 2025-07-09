from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow authors of an article to edit it.
    
    - Read permissions are allowed for any request (GET, HEAD, OPTIONS)
    - Write permissions are only allowed to the author of the article
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if permission is granted
        """
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to authenticated users
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access the specific object.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            obj: The object being accessed (Article instance)
            
        Returns:
            bool: True if permission is granted
        """
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the author of the article
        return obj.author == request.user


class IsOwnerOrCreateOnly(permissions.BasePermission):
    """
    Custom permission for user-specific article views.
    
    - Allows creating new articles for authenticated users
    - Only allows viewing own articles
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if permission is granted
        """
        # Only authenticated users can access this view
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access the specific object.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            obj: The object being accessed (Article instance)
            
        Returns:
            bool: True if permission is granted
        """
        # Users can only access their own articles
        return obj.author == request.user


class IsPublishedOrAuthor(permissions.BasePermission):
    """
    Custom permission to allow access to published articles by anyone,
    or any article by its author.
    
    - Published articles can be viewed by anyone (including anonymous users)
    - Draft articles can only be viewed by their authors
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            
        Returns:
            bool: True if permission is granted
        """
        # Allow all GET requests (we'll check specific permissions in has_object_permission)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For write operations, user must be authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access the specific object.
        
        Args:
            request: The HTTP request
            view: The view being accessed
            obj: The object being accessed (Article instance)
            
        Returns:
            bool: True if permission is granted
        """
        # If the article is published, anyone can read it
        if request.method in permissions.SAFE_METHODS and obj.status == 'published':
            return True
        
        # If the user is the author, they can access it regardless of status
        if request.user and request.user.is_authenticated and obj.author == request.user:
            return True
        
        # Otherwise, deny access
        return False