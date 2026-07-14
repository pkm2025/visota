"""Request ID middleware + request tracing for Visota ERP.

Injects X-Request-ID into every request/response for distributed tracing.
Integrates with structured logging via threadlocal request_id.
"""

import uuid

from apps.core.logging_utils import set_request_id


class RequestIDMiddleware:
    """Propagate or generate X-Request-ID for every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check incoming header or generate new
        request_id = request.headers.get("X-Request-ID")
        if not request_id or len(request_id) > 64:
            request_id = uuid.uuid4().hex[:12]

        request.request_id = request_id
        set_request_id(request_id)

        response = self.get_response(request)

        # Add to response headers
        response["X-Request-ID"] = request_id

        return response
