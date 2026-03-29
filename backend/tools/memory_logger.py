import logging
import io

class log_capture_handler(logging.Handler):
    """Custom logging handler to capture logs in memory for API exposure."""
    def __init__(self):
        super().__init__()
        self.logs = []
        self.max_logs = 100

    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

    def get_logs(self):
        return self.logs

# Global log capture instance
MEMORY_LOGS = log_capture_handler()
MEMORY_LOGS.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(message)s'))

def setup_global_capture():
    """Attach the memory logger to the root or specialized loggers."""
    root = logging.getLogger()
    root.addHandler(MEMORY_LOGS)
    # Also attach to specialized ones if needed
    for name in ["copilot.orchestrator", "copilot.agents"]:
        l = logging.getLogger(name)
        l.addHandler(MEMORY_LOGS)
