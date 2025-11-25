from django.db import models
import uuid

class Account(models.Model):
    account_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=64)
    subtype = models.CharField(max_length=64, null=True, blank=True)
    mask = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Batch(models.Model):
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    request_id = models.CharField(max_length=255, null=True, blank=True)
    total_transactions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Transaction(models.Model):
    INGESTION_STATUS_PENDING = 'pending'
    INGESTION_STATUS_PROCESSING = 'processing'
    INGESTION_STATUS_COMPLETED = 'completed'
    INGESTION_STATUS_FAILED = 'failed'

    INGESTION_STATUS_CHOICES = [
        (INGESTION_STATUS_PENDING, 'Pending'),
        (INGESTION_STATUS_PROCESSING, 'Processing'),
        (INGESTION_STATUS_COMPLETED, 'Completed'),
        (INGESTION_STATUS_FAILED, 'Failed'),
    ]

    transaction_id = models.CharField(max_length=255, unique=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    date = models.DateTimeField()
    authorized_date = models.DateField(null=True, blank=True)
    merchant_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=128, null=True, blank=True)
    ingestion_status = models.CharField(max_length=32, choices=INGESTION_STATUS_CHOICES, default=INGESTION_STATUS_PENDING)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['account', 'date']),
            models.Index(fields=['ingestion_status']),
        ]
