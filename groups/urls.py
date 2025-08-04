# groups/urls.py
from django.urls import path
from . import views

app_name = 'groups' # Define app_name for namespacing

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('create/', views.create_group_view, name='create_group'),
    path('<uuid:group_id>/', views.group_detail_view, name='group_detail'),
    path('<uuid:group_id>/edit/', views.edit_group, name='edit_group'),
    path('invitations/accept/<uuid:invitation_id>/', views.accept_invitation_view, name='accept_invitation'),
    path('invitations/decline/<uuid:invitation_id>/', views.decline_invitation_view, name='decline_invitation'),
    path('join/', views.join_group_by_code, name='join_group_by_code'),
    path('<uuid:group_id>/leave/', views.leave_group_view, name='leave_group'),
    path('<uuid:group_id>/delete/', views.delete_group_view, name='delete_group'),
    path('<uuid:group_id>/share-link/', views.share_group_link_view, name='share_group_link'),
]