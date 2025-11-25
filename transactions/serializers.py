from rest_framework import serializers

class AccountSerializer(serializers.Serializer):
    account_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    subtype = serializers.CharField(allow_null=True, required=False)
    mask = serializers.CharField(allow_null=True, required=False)

class TransactionItemSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
    account_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    iso_currency_code = serializers.CharField(max_length=3)
    date = serializers.DateTimeField()
    authorized_date = serializers.DateField(required=False, allow_null=True)
    name = serializers.CharField(allow_blank=True, required=False)
    merchant_name = serializers.CharField(allow_blank=True, required=False)
    payment_channel = serializers.CharField(required=False, allow_null=True)
    pending = serializers.BooleanField()

class IngestBatchSerializer(serializers.Serializer):
    accounts = AccountSerializer(many=True)
    transactions = TransactionItemSerializer(many=True)
    total_transactions = serializers.IntegerField()
    request_id = serializers.CharField(required=False, allow_null=True)
