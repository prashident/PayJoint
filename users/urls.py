# users/urls.py

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.index_view, name='index'),
    # The following are now handled by Django-Allauth,
    # so they should be removed from here.
    # path('signup/', views.signup_view, name='signup'),
    # path('login/', views.login_view, name='login'),
    # path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_detail_view, name='profile_detail'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
]