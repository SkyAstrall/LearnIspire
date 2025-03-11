from django.db import models
from django.utils import timezone
import uuid


class Payment(models.Model):
    PAYMENT_STATUS = (
        ("PENDING", "Pending"),
        ("INITIATED", "Initiated"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    )

    PAYMENT_METHODS = (
        ("CARD", "Credit/Debit Card"),
        ("UPI", "UPI"),
        ("NETBANKING", "Net Banking"),
        ("WALLET", "Wallet"),
    )

    student = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, blank=True
    )
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="PENDING")
    month_year = models.DateField(help_text="Month and year this payment is for")
    order_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    payment_details = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.email} - ₹{self.amount} ({self.get_status_display()})"

    class Meta:
        ordering = ["-created_at"]

    def mark_as_completed(self, transaction_id, payment_method, payment_details=None):
        """Mark payment as completed with transaction details."""
        self.status = "COMPLETED"
        self.transaction_id = transaction_id
        self.payment_method = payment_method
        self.payment_date = timezone.now()
        if payment_details:
            self.payment_details = payment_details
        self.save()

    def generate_payment_params(self):
        """Generate parameters for PayU payment gateway."""
        from django.conf import settings
        import hashlib

        # Basic payment information
        params = {
            "key": settings.PAYU_MERCHANT_KEY,
            "txnid": self.order_id,
            "amount": str(self.amount),
            "productinfo": f"Classes for {self.month_year.strftime('%B %Y')}",
            "firstname": self.student.first_name,
            "email": self.student.email,
            "phone": self.student.phone_number,
            "surl": f"{settings.SITE_URL}/payments/success/",
            "furl": f"{settings.SITE_URL}/payments/failure/",
            "service_provider": "payu_paisa",
        }

        # Generate hash
        hash_string = (
            f"{params['key']}|{params['txnid']}|{params['amount']}|{params['productinfo']}|"
            f"{params['firstname']}|{params['email']}|||||||||||{settings.PAYU_MERCHANT_SALT}"
        )

        params["hash"] = hashlib.sha512(hash_string.encode("utf-8")).hexdigest()

        return params


class TeacherEarning(models.Model):
    PAYMENT_STATUS = (
        ("PENDING", "Pending"),
        ("PROCESSED", "Processed"),
    )

    teacher = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="earnings"
    )
    month_year = models.DateField(help_text="Month and year these earnings are for")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    classes_conducted = models.PositiveIntegerField(default=0)
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS, default="PENDING"
    )
    payment_date = models.DateField(blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.teacher.email} - ₹{self.amount} for {self.month_year.strftime('%B %Y')}"

    class Meta:
        ordering = ["-month_year"]
        unique_together = ["teacher", "month_year"]

    def mark_as_processed(self, payment_reference, payment_date=None, notes=None):
        """Mark earnings as processed."""
        self.payment_status = "PROCESSED"
        self.payment_reference = payment_reference
        self.payment_date = payment_date or timezone.now().date()
        if notes:
            self.notes = notes
        self.save()

    @classmethod
    def calculate_for_teacher_month(cls, teacher, month_year):
        """Calculate earnings for a teacher for a specific month."""
        from scheduling.models import Class
        import calendar

        # Get month range
        year = month_year.year
        month = month_year.month
        _, last_day = calendar.monthrange(year, month)
        start_date = timezone.datetime(year, month, 1, 0, 0, 0)
        end_date = timezone.datetime(year, month, last_day, 23, 59, 59)

        # Get completed classes in the month
        completed_classes = Class.objects.filter(
            teacher=teacher,
            status="COMPLETED",
            start_time__gte=start_date,
            start_time__lte=end_date,
        )

        # Calculate earnings based on classes
        total_amount = 0
        for cls in completed_classes:
            # Logic to calculate per-class earnings
            # This is simplified - real implementation would need more complex logic
            # based on subject rates, etc.
            total_amount += 500  # Example fixed rate per class

        # Create or update earnings record
        earnings, created = cls.objects.update_or_create(
            teacher=teacher,
            month_year=month_year,
            defaults={
                "amount": total_amount,
                "classes_conducted": completed_classes.count(),
            },
        )

        return earnings
