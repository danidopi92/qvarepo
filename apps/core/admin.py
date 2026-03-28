from django.contrib import admin

from apps.core.models import AuditLog, Company, SystemSetting

admin.site.register(Company)
admin.site.register(SystemSetting)
admin.site.register(AuditLog)
