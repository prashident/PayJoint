# expenses/urls.py
from django.urls import path
from . import views

app_name = 'expenses' # Define app_name for namespacing

urlpatterns = [
    path('<uuid:group_id>/add/', views.add_expense_view, name='add_expense'),
    path('delete/<uuid:expense_id>/', views.delete_expense, name='delete_expense'),
    path('settle-split/<uuid:expense_id>/', views.settle_expense_part, name='settle_split'),
    # You might add paths for edit_expense, delete_expense later
]