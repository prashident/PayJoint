# expenses/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid
# Need to import Group from the groups app
from groups.models import Group

class Expense(models.Model):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='expenses',
        verbose_name="Group"
    )

    description = models.CharField(max_length=255, verbose_name="Expense Description")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    paid_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='paid_expenses',
        verbose_name="Paid By"
    )

    participants = models.ManyToManyField(
        User,
        related_name='participated_expenses',
        verbose_name="Participants",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.description} - (₹{self.amount}) by {self.paid_by.username} in {self.group.name}"