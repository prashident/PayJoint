# payjoint/urls.py
from django.contrib import admin
from django.urls import path, include # Import include
from django.conf import settings # For media files
from django.conf.urls.static import static # For media files

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')), # Include user-related URLs at the root or /users/
    path('groups/', include('groups.urls')), # Include group-related URLs
    path('expenses/', include('expenses.urls')), # Include expense-related URLs (relative to groups where applicable)
    # Consider what your default landing page is for anonymous users, might be users:login or users:signup
    path('', include('users.urls')), # Make login/signup accessible at the root or define a root redirect
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Ensure static files are also served