from django.db import models


class Subject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="subject_icons/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Grade(models.Model):
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["order"]


class Board(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class PricingRule(models.Model):
    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, related_name="pricing_rules"
    )
    board = models.ForeignKey(
        Board, on_delete=models.CASCADE, related_name="pricing_rules"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="pricing_rules"
    )
    price_per_session = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject.name} - {self.grade.name} ({self.board.name}): ₹{self.price_per_session}"

    class Meta:
        unique_together = ["grade", "board", "subject"]
        ordering = ["grade__order", "subject__name"]


class Configuration(models.Model):
    """Model for storing system configuration values."""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.key

    @classmethod
    def get_value(cls, key, default=None):
        """Get configuration value by key."""
        try:
            config = cls.objects.get(key=key)
            return config.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, key, value, description=None):
        """Set configuration value by key."""
        config, created = cls.objects.update_or_create(
            key=key, defaults={"value": value, "description": description or ""}
        )
        return config
