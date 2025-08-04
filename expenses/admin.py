# expenses/admin.py
from django.contrib import admin
from .models import Expense # Import model from within this app

admin.site.register(Expense)