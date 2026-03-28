from django.contrib import admin

from apps.customers.models import Customer, CustomerContact, CustomerDocument, CustomerNote, Node

admin.site.register(Node)
admin.site.register(Customer)
admin.site.register(CustomerContact)
admin.site.register(CustomerNote)
admin.site.register(CustomerDocument)
