import traceback
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(object)
    finished = pyqtSignal()


class ApiWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.result.emit(self.fn(*self.args, **self.kwargs))
        except Exception as exc:
            self.signals.error.emit(exc)
        finally:
            self.signals.finished.emit()
