from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from transactions.models import Account, Transaction

class IngestionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_batch_ingest_creates_accounts_and_transactions_idempotent(self):
        payload = {
            "accounts": [
                {"account_id": "acc_123", "name": "Business Checking", "type": "depository", "subtype": "checking", "mask": "1111"}
            ],
            "transactions": [
                {
                    "transaction_id": "tx_1",
                    "account_id": "acc_123",
                    "amount": -100.00,
                    "iso_currency_code": "USD",
                    "date": "2025-10-30T08:00:00Z",
                    "authorized_date": "2025-10-30",
                    "name": "Amazon Marketplace",
                    "merchant_name": "Amazon",
                    "payment_channel": "online",
                    "pending": False
                }
            ],
            "total_transactions": 1,
            "request_id": "req_test"
        }

        url = reverse('ingest-transactions')
        r1 = self.client.post(url, payload, format='json')
        self.assertEqual(r1.status_code, 202)
        self.assertTrue(Account.objects.filter(account_id='acc_123').exists())
        self.assertTrue(Transaction.objects.filter(transaction_id='tx_1').exists())

        r2 = self.client.post(url, payload, format='json')
        self.assertEqual(r2.status_code, 202)
        self.assertEqual(Transaction.objects.filter(transaction_id='tx_1').count(), 1)
