import time, random, logging
from celery import shared_task, Task
from .models import Batch, Transaction
from .categorizer import RuleBasedCategorizer
from django.db import transaction as db_transaction
from middleware.observability import generate_correlation_id

logger = logging.getLogger("tasks")


class ObservedTask(Task):
    """Base task that ensures correlation ID is passed in context."""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        correlation_id = kwargs.get("correlation_id", "unknown")
        logger.exception(
            "task_failed",
            extra={
                "correlation_id": correlation_id,
                "task_id": task_id,
                "args": args,
                "kwargs": kwargs,
                "error": str(exc),
            }
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(bind=True, base=ObservedTask, max_retries=3, default_retry_delay=10)
def process_batch_enrichment(self, batch_id_str, correlation_id=None):
    correlation_id = correlation_id or self.request.id or generate_correlation_id()
    task_start = time.time()
    logger.info(
        "task_started",
        extra={
            "correlation_id": correlation_id,
            "task_name": self.name,
            "batch_id": batch_id_str,
            "timestamp": task_start,
        }
    )

    try:
        batch = Batch.objects.get(batch_id=batch_id_str)
    except Batch.DoesNotExist:
        logger.error(
            "Batch not found",
            extra={"correlation_id": correlation_id, "batch_id": batch_id_str}
        )
        return

    categorizer = RuleBasedCategorizer()

    # Ensure the select_for_update happens inside a transaction
    with db_transaction.atomic():
        tx_qs = (
            batch.transactions
            .select_for_update(skip_locked=True)
            .all()
        )
        transactions_list = list(tx_qs)

    # Process each transaction independently
    for tx in transactions_list:
        if tx.ingestion_status == Transaction.INGESTION_STATUS_COMPLETED:
            continue

        tx_start = time.time()
        tx_info = {
            "correlation_id": correlation_id,
            "batch_id": batch_id_str,
            "transaction_id": tx.transaction_id
        }

        try:
            with db_transaction.atomic():
                tx.ingestion_status = Transaction.INGESTION_STATUS_PROCESSING
                tx.save(update_fields=['ingestion_status', 'updated_at'])

            # Simulate processing delay
            time.sleep(random.uniform(0.5, 1.0))

            category = categorizer.categorize(tx.merchant_name, tx.description)

            with db_transaction.atomic():
                tx.category = category
                tx.ingestion_status = Transaction.INGESTION_STATUS_COMPLETED
                tx.save(update_fields=['category', 'ingestion_status', 'updated_at'])

            logger.info(
                "transaction_completed",
                extra={**tx_info, "duration_sec": round(time.time() - tx_start, 4)}
            )

        except Exception as e:
            logger.exception(
                "transaction_failed",
                extra={**tx_info, "error": str(e), "duration_sec": round(time.time() - tx_start, 4)}
            )
            with db_transaction.atomic():
                tx.ingestion_status = Transaction.INGESTION_STATUS_FAILED
                tx.save(update_fields=['ingestion_status', 'updated_at'])
            continue

    logger.info(
        "task_completed",
        extra={
            "correlation_id": correlation_id,
            "task_name": self.name,
            "batch_id": batch_id_str,
            "duration_sec": round(time.time() - task_start, 4)
        }
    )
