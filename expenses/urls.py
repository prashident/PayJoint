# expenses/urls.py
from django.urls import path
from . import views

app_name = 'expenses' # Define app_name for namespacing

urlpatterns = [
    path('<uuid:group_id>/add/', views.add_expense_view, name='add_expense'),
    path('delete/<uuid:expense_id>/', views.delete_expense, name='delete_expense'),
    path('settle-split/<uuid:expense_id>/', views.settle_expense_part, name='settle_split'),
    path('add/dashboard/', views.add_dashboard_expense, name='add_dashboard_expense'),
    # Change from uuid to str to accept the shorter code
path('group/<str:invite_code>/settle-all/', views.bulk_settle_group, name='bulk_settle_group'),
    # You might add paths for edit_expense, delete_expense later
]