from django.contrib import admin

from apps.billing.models import Currency, Invoice, InvoiceItem, Payment, SuspensionEvent

admin.site.register(Currency)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Payment)
admin.site.register(SuspensionEvent)
