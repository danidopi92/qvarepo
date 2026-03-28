import uuid

from django.utils.deprecation import MiddlewareMixin


class RequestAuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = str(uuid.uuid4())
