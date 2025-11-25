from django.test import TestCase
from transactions.models import Account, Transaction, Batch
from transactions.tasks import process_batch_enrichment
from decimal import Decimal
import datetime

class EnrichmentTaskTests(TestCase):
    def test_enrichment_marks_transactions_completed_and_idempotent(self):
        acct = Account.objects.create(account_id='acc_t', name='A', type='depository')
        batch = Batch.objects.create(total_transactions=1, request_id='r1')
        tx = Transaction.objects.create(
            transaction_id='tx_e1',
            account=acct,
            amount=Decimal('-42.00'),
            currency='USD',
            date=datetime.datetime.utcnow(),
            merchant_name='Amazon',
            description='Amazon purchase',
            ingestion_status=Transaction.INGESTION_STATUS_PENDING,
            batch=batch
        )

        process_batch_enrichment(str(batch.batch_id))
        tx.refresh_from_db()
        self.assertEqual(tx.ingestion_status, Transaction.INGESTION_STATUS_COMPLETED)
        self.assertIsNotNone(tx.category)

        category_before = tx.category
        process_batch_enrichment(str(batch.batch_id))
        tx.refresh_from_db()
        self.assertEqual(tx.ingestion_status, Transaction.INGESTION_STATUS_COMPLETED)
        self.assertEqual(tx.category, category_before)
