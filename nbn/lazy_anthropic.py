"""Keep collector/Desk startup independent of unused legacy provider credentials."""
import threading

from . import config


class LazyAnthropic:
    def __init__(self, **options):
        self._options = options
        self._instance = None
        self._lock = threading.Lock()

    def __getattr__(self, name):
        if config.OPERATING_MODE == "infrastructure":
            raise RuntimeError("Legacy Anthropic calls are disabled in infrastructure mode")
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    import anthropic
                    self._instance = anthropic.Anthropic(**self._options)
        return getattr(self._instance, name)
