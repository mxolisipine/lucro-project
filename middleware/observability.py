import time
import uuid
import logging
import json
from django.utils.deprecation import MiddlewareMixin
from project.settings import set_correlation_id, get_correlation_id
http_logger = logging.getLogger("observability.http")




class ObservabilityMiddleware(MiddlewareMixin):

    def process_request(self, request):
        request._start_time = time.time()

        # correlation id (from header or new)
        cid = request.headers.get("X-Correlation-ID")
        set_correlation_id(cid)

        request.correlation_id = get_correlation_id()

        request.start_time = time.time()
        json_data = json.loads(request.body)
        http_logger.info(
            "request_started",
            extra={
                "type":"request",
                "correlation_id": request.correlation_id,
                "method": request.method,
                "path": request.path,
                "client_ip": request.META.get("REMOTE_ADDR"),
                "user_agent": request.headers.get("User-Agent"),
                "status_code":0,
                "response_bytes":0,
                "duration_sec": 0,
            }
        )

    def process_response(self, request, response):
        correlation_id = getattr(request, "correlation_id", get_correlation_id())
        duration = None

        if hasattr(request, "start_time"):
            duration = round(time.time() - request.start_time, 4)

        http_logger.info(
            "request_completed",
            extra={
                "type":"response",
                "correlation_id": correlation_id,
                "method": getattr(request, "method", None),
                "path": getattr(request, "path", None),
                "client_ip": request.META.get("REMOTE_ADDR"),
                "user_agent": request.headers.get("User-Agent"),
                "status_code": response.status_code,
                "duration_sec": duration,
                "response_bytes": getattr(response, "content", None).__sizeof__() if hasattr(response, "content") else None,
            }
        )

        # Attach correlation ID to client response
        response["X-Correlation-ID"] = correlation_id

        return response
