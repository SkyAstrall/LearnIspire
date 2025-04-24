from django.db import models
from django.utils import timezone

class PricingRule(models.Model):
    """
    Model to store pricing rules for subjects based on grade and board.
    """
    subject = models.ForeignKey('common.Subject', on_delete=models.CASCADE, related_name='pricing_rules')
    grade = models.ForeignKey('common.Grade', on_delete=models.CASCADE)
    board = models.ForeignKey('common.Board', on_delete=models.CASCADE)
    
    price_per_session = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['subject', 'grade', 'board']
        ordering = ['grade', 'subject']
    
    def __str__(self):
        return f"{self.subject.name} - {self.grade.name} - {self.board.name} - ₹{self.price_per_session}"
    
    @classmethod
    def get_price_for_subject(cls, subject, grade, board):
        """Get price for a specific subject, grade, and board combination."""
        rule = cls.objects.filter(
            subject=subject,
            grade=grade,
            board=board,
            is_active=True
        ).first()
        
        if rule:
            return rule.price_per_session
        
        return None  # No pricing rule found
    
    @classmethod
    def calculate_monthly_fee(cls, subject, grade, board, classes_per_week=3):
        """Calculate monthly fee for a subject."""
        price_per_session = cls.get_price_for_subject(subject, grade, board)
        
        if price_per_session:
            # Calculate based on 4 weeks per month
            return float(price_per_session) * classes_per_week * 4
        
        return None  # No pricing available