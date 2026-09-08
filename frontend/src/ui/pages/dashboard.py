from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from ...api.client import ApiError
from ...workers import ApiWorker
from ..common import BusyBar, StateBanner, title_block


class DashboardPage(QWidget):
    navigate = pyqtSignal(str)
    session_expired = pyqtSignal()

    def __init__(self, api, role):
        super().__init__(); self.api, self.role, self.worker = api, role, None
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        layout.addLayout(title_block('Dashboard', 'A live overview of records this account is allowed to retrieve.'))
        self.busy = BusyBar(); layout.addWidget(self.busy)
        self.banner = StateBanner(); self.banner.retry.clicked.connect(self.refresh); layout.addWidget(self.banner)
        self.grid = QGridLayout(); self.cards = {}; layout.addLayout(self.grid); layout.addStretch()
        allowed = {
            'ADMIN': [('students', 'Students', 'students'), ('programs', 'Programs', 'programs'), ('courses', 'Courses', 'courses'), ('course-offerings', 'Offerings', 'course-offerings'), ('enrollments', 'Enrollments', 'enrollments'), ('grades', 'Grades', 'grades')],
            'REGISTRAR': [('students', 'Students', 'students'), ('programs', 'Programs', 'programs'), ('courses', 'Courses', 'courses'), ('course-offerings', 'Offerings', 'course-offerings'), ('enrollments', 'Enrollments', 'enrollments'), ('grades', 'Grades', 'grades')],
            'INSTRUCTOR': [('course-offerings', 'Assigned offerings', 'course-offerings'), ('enrollments', 'Enrolled students', 'enrollments'), ('grades', 'Grade records', 'grades')],
            'STUDENT': [('students', 'My profile', 'profile'), ('enrollments', 'My enrollments', 'records'), ('grades', 'My grades', 'records')],
        }[role]
        self.resources = allowed
        for index, (key, label, route) in enumerate(allowed):
            card = QFrame(); card.setObjectName('card'); box = QVBoxLayout(card)
            title = QLabel(label); title.setObjectName('muted'); value = QLabel('—'); value.setObjectName('metric')
            button = QPushButton('Open'); button.clicked.connect(lambda _, target=route: self.navigate.emit(target))
            box.addWidget(title); box.addWidget(value); box.addWidget(button); self.cards[key] = value
            self.grid.addWidget(card, index // 3, index % 3)

    def showEvent(self, event): super().showEvent(event); self.refresh()

    def refresh(self):
        self.banner.hide(); self.busy.show()
        self.worker = ApiWorker(self._counts)
        self.worker.signals.result.connect(self._loaded); self.worker.signals.error.connect(self._error)
        self.worker.signals.finished.connect(self.busy.hide); QThreadPool.globalInstance().start(self.worker)

    def _counts(self):
        return {key: self.api.list(key, page=1, per_page=1).get('count', 0) for key, _, _ in self.resources}

    def _loaded(self, counts):
        for key, value in counts.items(): self.cards[key].setText(str(value))

    def _error(self, error):
        if isinstance(error, ApiError) and error.status == 401: self.session_expired.emit()
        else: self.banner.show_state(str(error))
