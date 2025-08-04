# groups/admin.py
from django.contrib import admin
from .models import Group, Invitation # Import models from within this app

admin.site.register(Group)
admin.site.register(Invitation)