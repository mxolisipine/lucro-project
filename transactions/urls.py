from django.urls import path
from .views import TransactionIngestAPIView, AccountSummaryAPIView, HealthCheckAPIView

urlpatterns = [
    path('health/', HealthCheckAPIView.as_view(), name='health-check'),
    path('integrations/transactions/', TransactionIngestAPIView.as_view(), name='ingest-transactions'),
    path('reports/account/<str:account_id>/summary', AccountSummaryAPIView.as_view(), name='account-summary'),
]
