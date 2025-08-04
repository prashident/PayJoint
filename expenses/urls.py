# expenses/urls.py
from django.urls import path
from . import views

app_name = 'expenses' # Define app_name for namespacing

urlpatterns = [
    path('<uuid:group_id>/add/', views.add_expense_view, name='add_expense'),
    # You might add paths for edit_expense, delete_expense later
]