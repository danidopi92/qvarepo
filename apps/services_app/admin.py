from django.contrib import admin

from apps.services_app.models import CustomerService, Equipment, ServicePlan

admin.site.register(ServicePlan)
admin.site.register(CustomerService)
admin.site.register(Equipment)
