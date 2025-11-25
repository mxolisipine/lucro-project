import logging
import time
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction as db_transaction, IntegrityError
from django.http import JsonResponse
from django.db import connection
import redis
from rest_framework.generics import GenericAPIView
from rest_framework import serializers
from django.db.models import Sum, Count, Q

from .serializers import IngestBatchSerializer
from .models import Account, Transaction, Batch
from .tasks import process_batch_enrichment

# Structured logger
logger = logging.getLogger(__name__)


############################
# CORRELATION ID UTIL
############################
def get_correlation_id(request):
    return request.headers.get("X-Correlation-ID", str(uuid.uuid4()))


class HealthCheckAPIView(GenericAPIView):
    def get(self, request):
        
        correlation_id = get_correlation_id(request)

        logger.info("healthcheck_requested", extra={"correlation_id": correlation_id})

        status_obj = {"status": "ok", "correlation_id": correlation_id}

        # DB Check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
        except Exception as e:
            logger.error("database_unhealthy", extra={"error": str(e)})
            status_obj["database"] = f"error: {str(e)}"
            status_obj["status"] = "unhealthy"
        else:
            status_obj["database"] = "ok"

        # Redis Check
        try:
            r = redis.Redis(host="redis", port=6379, db=0)
            r.ping()
        except Exception as e:
            logger.error("redis_unhealthy", extra={"error": str(e)})
            status_obj["redis"] = f"error: {str(e)}"
            status_obj["status"] = "unhealthy"
        else:
            status_obj["redis"] = "ok"

        logger.info("healthcheck_response", extra=status_obj)

        return JsonResponse(status_obj)


class TransactionIngestAPIView(APIView):
    def post(self, request):
        
        start_time = time.time()
        correlation_id = get_correlation_id(request)

        logger.info(
            "transaction_ingest_received",
            extra={
                "correlation_id": correlation_id,
                "payload_bytes": len(request.body or b"")
            }
        )

        serializer = IngestBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with db_transaction.atomic():

                logger.info(
                    "creating_batch",
                    extra={"correlation_id": correlation_id, "transaction_count": len(data['transactions'])}
                )

                batch = Batch.objects.create(
                    request_id=data.get('request_id'),
                    total_transactions=len(data['transactions'])
                )

                accounts_map = {}
                for acc in data['accounts']:
                    account_obj, _ = Account.objects.get_or_create(
                        account_id=acc['account_id'],
                        defaults={
                            'name': acc['name'],
                            'type': acc['type'],
                            'subtype': acc.get('subtype'),
                            'mask': acc.get('mask'),
                        }
                    )
                    accounts_map[acc['account_id']] = account_obj

                transaction_objs = []
                for tx in data['transactions']:
                    acct = accounts_map.get(tx['account_id'])
                    if not acct:
                        raise IntegrityError(f"Account {tx['account_id']} missing in payload")

                    tx_obj, created = Transaction.objects.get_or_create(
                        transaction_id=tx['transaction_id'],
                        defaults={
                            'account': acct,
                            'amount': tx['amount'],
                            'currency': tx['iso_currency_code'],
                            'date': tx['date'],
                            'authorized_date': tx.get('authorized_date'),
                            'merchant_name': tx.get('merchant_name') or tx.get('name'),
                            'description': tx.get('name'),
                            'ingestion_status': Transaction.INGESTION_STATUS_PENDING,
                            'batch': batch
                        }
                    )
                    transaction_objs.append(tx_obj)

            logger.info(
                "dispatching_enrichment_task",
                extra={"correlation_id": correlation_id, "batch_id": str(batch.batch_id)}
            )

            process_batch_enrichment.delay(str(batch.batch_id))

            duration = round(time.time() - start_time, 3)
            logger.info(
                "transaction_ingest_success",
                extra={
                    "correlation_id": correlation_id,
                    "batch_id": str(batch.batch_id),
                    "duration_sec": duration
                }
            )

            return Response(
                {
                    "batch_id": str(batch.batch_id),
                    "total_transactions": batch.total_transactions,
                    "correlation_id": correlation_id,
                    "duration_sec": duration,
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.exception(
                "transaction_ingest_failed",
                extra={"correlation_id": correlation_id, "error": str(e)}
            )
            return Response(
                {"detail": "Failed to ingest batch", "correlation_id": correlation_id},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DateRangeParamsSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class AccountSummaryAPIView(GenericAPIView):
    def get(self, request, account_id):
        
        start_time = time.time()
        correlation_id = get_correlation_id(request)

        logger.info(
            "account_summary_requested",
            extra={"correlation_id": correlation_id, "account_id": account_id}
        )

        params = DateRangeParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        start = params.validated_data['start_date']
        end = params.validated_data['end_date']

        qs = Transaction.objects.filter(
            account__account_id=account_id,
            date__date__gte=start,
            date__date__lte=end,
        )

        metrics = qs.aggregate(
            total_transactions=Count('id'),
            total_spend=Sum('amount', filter=Q(amount__lt=0)),
            total_income=Sum('amount', filter=Q(amount__gt=0)),
        )

        total_spend = metrics['total_spend'] or 0
        total_income = metrics['total_income'] or 0
        net = (total_spend or 0) + (total_income or 0)

        top = (
            qs
            .filter(category__isnull=False)
            .values('category')
            .annotate(total_spend=Sum('amount', filter=Q(amount__lt=0)), transaction_count=Count('id'))
            .order_by('total_spend')[:3]
        )

        status_counts = qs.values('ingestion_status').annotate(count=Count('id'))
        status_map = {s['ingestion_status']: s['count'] for s in status_counts}

        duration = round(time.time() - start_time, 3)

        logger.info(
            "account_summary_response",
            extra={
                "correlation_id": correlation_id,
                "account_id": account_id,
                "duration_sec": duration,
                "total_transactions": metrics['total_transactions'] or 0,
            }
        )

        return Response(
            {
                "account_id": account_id,
                "date_range": {"start": start.isoformat(), "end": end.isoformat()},
                "metrics": {
                    "total_transactions": metrics['total_transactions'] or 0,
                    "total_spend": float(abs(total_spend)) if total_spend else 0.0,
                    "total_income": float(total_income) if total_income else 0.0,
                    "net": float(net),
                },
                "top_categories": [
                    {
                        "category": t['category'],
                        "total_spend": float(abs(t['total_spend'])) if t['total_spend'] else 0.0,
                        "transaction_count": t['transaction_count']
                    }
                    for t in top
                ],
                "processing_status": {
                    "pending": status_map.get(Transaction.INGESTION_STATUS_PENDING, 0),
                    "processing": status_map.get(Transaction.INGESTION_STATUS_PROCESSING, 0),
                    "completed": status_map.get(Transaction.INGESTION_STATUS_COMPLETED, 0),
                    "failed": status_map.get(Transaction.INGESTION_STATUS_FAILED, 0),
                },
                "correlation_id": correlation_id,
                "duration_sec": duration
            }
        )
