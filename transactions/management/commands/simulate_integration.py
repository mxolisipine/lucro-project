from django.core.management.base import BaseCommand
import uuid, random, datetime, requests
from django.conf import settings

class Command(BaseCommand):
    help = "Generate realistic batch of 10-15 transactions and post to ingestion endpoint"

    def handle(self, *args, **options):
        base_url = getattr(settings, 'SIMULATE_BASE_URL', 'http://web:8000')
        endpoint = f"{base_url}/api/integrations/transactions/"
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        account_id = f"acc_{uuid.uuid4().hex[:8]}"

        accounts = [{
            "account_id": account_id,
            "name": "Business Checking",
            "type": "depository",
            "subtype": "checking",
            "mask": "1111"
        }]

        merchants = ["Amazon Marketplace", "Stripe", "Uber", "AWS", "Starbucks", "PayPal", "Lyft", "Adobe"]
        txs = []
        n = random.randint(10, 15)
        now = datetime.datetime.utcnow()
        for i in range(n):
            txn = {
                "transaction_id": f"tx_{uuid.uuid4().hex[:12]}",
                "account_id": account_id,
                "amount": round(random.choice([-1, 1]) * round(random.uniform(5, 1500), 2), 2),
                "iso_currency_code": "USD",
                "date": (now - datetime.timedelta(days=random.randint(0, 30))).isoformat() + "Z",
                "authorized_date": (now - datetime.timedelta(days=random.randint(0, 30))).date().isoformat(),
                "name": random.choice(merchants),
                "merchant_name": random.choice(merchants),
                "payment_channel": random.choice(["online", "in store"]),
                "pending": False
            }
            txs.append(txn)

        payload = {
            "accounts": accounts,
            "transactions": txs,
            "total_transactions": len(txs),
            "request_id": req_id
        }

        print("Posting batch with request_id:", req_id)
        try:
            resp = requests.post(endpoint, json=payload, timeout=10)
            print("Status:", resp.status_code, resp.text)
        except Exception as e:
            print("Failed to post:", e)
