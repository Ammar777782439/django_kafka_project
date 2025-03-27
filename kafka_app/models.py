from django.db import models
from django.utils import timezone

class MessageAnalytics(models.Model):
    """Model for storing message analytics data"""
    # Time periods
    PERIOD_HOURLY = 'hourly'
    PERIOD_DAILY = 'daily'
    PERIOD_WEEKLY = 'weekly'
    PERIOD_MONTHLY = 'monthly'

    PERIOD_CHOICES = [
        (PERIOD_HOURLY, 'Hourly'),
        (PERIOD_DAILY, 'Daily'),
        (PERIOD_WEEKLY, 'Weekly'),
        (PERIOD_MONTHLY, 'Monthly'),
    ]

    # Message types
    TYPE_ALL = 'all'
    TYPE_TEXT = 'text'
    TYPE_SOFT_DELETE = 'soft_delete'

    TYPE_CHOICES = [
        (TYPE_ALL, 'All Messages'),
        (TYPE_TEXT, 'Text Messages'),
        (TYPE_SOFT_DELETE, 'Soft Deleted Messages'),
    ]

    # Fields
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateTimeField()
    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message_count = models.IntegerField(default=0)
    unique_senders = models.IntegerField(default=0)
    unique_receivers = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('period', 'period_start', 'message_type')
        indexes = [
            models.Index(fields=['period', 'period_start']),
            models.Index(fields=['message_type']),
        ]
        verbose_name_plural = 'Message Analytics'

    def __str__(self):
        return f"{self.get_period_display()} analytics for {self.get_message_type_display()} starting {self.period_start}"


class KeywordAnalytics(models.Model):
    """Model for storing keyword analytics data"""
    keyword = models.CharField(max_length=50)
    occurrences = models.IntegerField(default=0)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'Keyword Analytics'
        indexes = [
            models.Index(fields=['keyword']),
            models.Index(fields=['occurrences']),
        ]

    def __str__(self):
        return f"{self.keyword} ({self.occurrences} occurrences)"


class UserActivityAnalytics(models.Model):
    """Model for storing user activity analytics data"""
    username = models.CharField(max_length=150)
    messages_sent = models.IntegerField(default=0)
    messages_received = models.IntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'User Activity Analytics'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        return f"{self.username} (sent: {self.messages_sent}, received: {self.messages_received})"


class MessageLifetimeAnalytics(models.Model):
    """Model for storing message lifetime analytics data"""
    # Lifetime ranges in minutes
    LIFETIME_RANGE_CHOICES = [
        ('0-1', 'Less than 1 minute'),
        ('1-5', '1-5 minutes'),
        ('5-15', '5-15 minutes'),
        ('15-30', '15-30 minutes'),
        ('30-60', '30-60 minutes'),
        ('60-180', '1-3 hours'),
        ('180-360', '3-6 hours'),
        ('360-720', '6-12 hours'),
        ('720-1440', '12-24 hours'),
        ('1440+', 'More than 24 hours'),
    ]

    lifetime_range = models.CharField(max_length=10, choices=LIFETIME_RANGE_CHOICES)
    message_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Message Lifetime Analytics'
        indexes = [
            models.Index(fields=['lifetime_range']),
        ]

    def __str__(self):
        return f"{self.get_lifetime_range_display()}: {self.message_count} messages"
