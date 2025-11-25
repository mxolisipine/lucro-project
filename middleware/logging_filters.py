import logging

class EnsureObservabilityFields(logging.Filter):
    """
    Ensures every log record contains all fields required by the JSON formatter.
    Prevents KeyError exceptions when Django logs internally.
    """

    DEFAULTS = {
        "correlation_id": "-",
        "method": "-",
        "type": "-",
        "client_ip": "-",
        "user_agent": "-",
        "path": "-",
        "status_code": "-",
        "response_bytes": "-",
        "duration_sec": "-",
        "task_name": "-",
        "task_id": "-",
        "queue": "-",
        "retries": "-",
    }

    def filter(self, record):
        for key, value in self.DEFAULTS.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True
