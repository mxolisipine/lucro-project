from django.contrib import admin
from .models import Account, Batch, Transaction

admin.site.register(Account)
admin.site.register(Batch)
admin.site.register(Transaction)
