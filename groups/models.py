# groups/models.py
from django.db import models
from django.contrib.auth.models import User # Group model needs User
import uuid
from django.db.models import Sum
from decimal import Decimal

class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Group Name")
    description = models.TextField(blank=True,null = True, verbose_name="Group Description (optional)")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_groups',
        verbose_name="Created By"
    )

    members = models.ManyToManyField(
        User,
        related_name='joined_groups',
        verbose_name="Group Members",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    image = models.ImageField(upload_to='group_images/', blank=True, null=True, verbose_name="Group Image")

    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Group Budget (Optional)",
        help_text="Set an optional budget for this group (e.g., 5000.00)"
    )

    GROUP_TYPE_CHOICES = [
        ('Trip', 'Trip'),
        ('Home', 'Home'),
        ('Others', 'Others'),
    ]
    group_type = models.CharField(
        max_length=10,
        choices=GROUP_TYPE_CHOICES,
        default='Others',
        verbose_name="Group Type"
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Start Date (for Trips)"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="End Date (for Trips)"
    )
    individual_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Individual Budget (for Trips)",
        help_text="Optional: Budget per person for this trip"
    )

    monthly_home_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monthly Home Budget",
        help_text="Optional: Monthly budget for this home group"
    )

    class Meta:
        verbose_name = "Group"
        verbose_name_plural = "Groups"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_total_expenses_amount(self):
        """Calculates the sum of all expenses in this group."""
        total_sum = self.expenses.aggregate(total=Sum('amount'))['total']
        return total_sum if total_sum is not None else Decimal('0.00')

    def get_remaining_budget(self):
        """Calculates the remaining budget."""
        if self.budget is None:
            return None
        total_spent = self.get_total_expenses_amount()
        return self.budget - total_spent


# Move Invitation model here too, as it's tightly coupled with Group
class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name="Group"
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name="Invited By"
    )
    invited_email = models.EmailField(verbose_name="Invited Email")
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('decline', 'Declined'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        unique_together = ('group', 'invited_email', 'status')
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation to {self.group.name} for {self.invited_email} ({self.status})"