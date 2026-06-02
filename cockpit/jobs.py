"""Run callables off the UI thread and deliver results back via signals."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _WorkerSignals(QObject):
    done = Signal(object)
    error = Signal(str)


class _Worker(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.setAutoDelete(False)  # keep alive until queued signal is delivered
        self.fn = fn
        self.signals = _WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 - report all failures to caller
            self.signals.error.emit(str(exc))
        else:
            self.signals.done.emit(result)


class JobRunner:
    """Submit a no-arg callable; on_done/on_error fire on the UI thread."""

    def __init__(self):
        self.pool = QThreadPool.globalInstance()

    def submit(self, fn, on_done=None, on_error=None):
        worker = _Worker(fn)
        if on_done is not None:
            worker.signals.done.connect(on_done)
        if on_error is not None:
            worker.signals.error.connect(on_error)
        self.pool.start(worker)
        return worker
