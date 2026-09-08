from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget)
from ...api.client import ApiError
from ...workers import ApiWorker
from ..common import BusyBar, StateBanner, title_block


class AcademicRecordPage(QWidget):
    session_expired = pyqtSignal()

    def __init__(self, api, student_id=None):
        super().__init__(); self.api, self.student_id, self.worker = api, student_id, None
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 20, 24, 20)
        header = QHBoxLayout(); header.addLayout(title_block('Academic Record', 'Enrollments and grades grouped by academic term.'), 1)
        refresh = QPushButton('Refresh'); refresh.clicked.connect(self.refresh); header.addWidget(refresh); layout.addLayout(header)
        self.busy = BusyBar(); layout.addWidget(self.busy)
        self.banner = StateBanner(); self.banner.retry.clicked.connect(self.refresh); layout.addWidget(self.banner)
        self.profile_card = QFrame(); self.profile_card.setObjectName('card'); profile_layout = QVBoxLayout(self.profile_card)
        profile_title = QLabel('Student profile'); profile_title.setStyleSheet('font-weight:700;font-size:12pt;')
        self.profile_text = QLabel(); self.profile_text.setWordWrap(True); self.profile_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        profile_layout.addWidget(profile_title); profile_layout.addWidget(self.profile_text); self.profile_card.hide(); layout.addWidget(self.profile_card)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget(); self.cards = QVBoxLayout(self.content); self.cards.addStretch(); scroll.setWidget(self.content); layout.addWidget(scroll, 1)

    def set_student(self, student_id): self.student_id = student_id; self.refresh()
    def showEvent(self, event):
        super().showEvent(event)
        if self.student_id: self.refresh()
        else: self._find_own_student()

    def _find_own_student(self):
        self.busy.show(); self.worker = ApiWorker(self.api.list, 'students', page=1, per_page=1)
        self.worker.signals.result.connect(lambda data: self.set_student(data['results'][0]['id']) if data.get('results') else self.banner.show_state('No student profile is linked to this account.', False))
        self.worker.signals.error.connect(self._error); self.worker.signals.finished.connect(self.busy.hide); QThreadPool.globalInstance().start(self.worker)

    def refresh(self):
        if not self.student_id: return
        self.banner.hide(); self.busy.show(); self.worker = ApiWorker(self._load_record)
        self.worker.signals.result.connect(self._loaded); self.worker.signals.error.connect(self._error)
        self.worker.signals.finished.connect(self.busy.hide); QThreadPool.globalInstance().start(self.worker)

    def _clear(self):
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _load_record(self):
        student = self.api.get('students', self.student_id)
        program = self.api.get('programs', student['program_id'])
        response = self.api.request('GET', f'students/{self.student_id}/academic-record', params={'per_page': 100})
        return student, program, response

    def _loaded(self, payload):
        student, program, response = payload
        name = ' '.join(part for part in [student.get('first_name'), student.get('middle_name'), student.get('last_name'), student.get('suffix')] if part)
        self.profile_text.setText(f"{student.get('student_number')} · {name}\n{program.get('code')} — {program.get('name')}  |  Year level: {student.get('year_level')}  |  Status: {student.get('status')}")
        self.profile_card.show()
        self._clear(); terms = response.get('data', {}).get('terms', [])
        if not terms: self.banner.show_state('No academic records are available for this student.', False); return
        for group in terms:
            term = group['term']; card = QFrame(); card.setObjectName('card'); box = QVBoxLayout(card)
            title = QLabel(f"{term['academic_year']} · {term['semester'].title()}"); title.setStyleSheet('font-weight:700;font-size:13pt;'); box.addWidget(title)
            for row in group['records']:
                grade = row.get('grade'); course = row['course']; enrollment = row['enrollment']
                text = f"{course['course_code']} — {course['course_title']} ({course['units']} units)\nEnrollment: {enrollment['status']}"
                text += f"  |  Midterm: {grade.get('midterm_grade') or '—'}  |  Final: {grade.get('final_grade') or '—'}  |  {grade.get('remarks') or grade.get('status')}" if grade else '  |  Grade pending'
                label = QLabel(text); label.setWordWrap(True); label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); box.addWidget(label)
            self.cards.insertWidget(self.cards.count() - 1, card)

    def _error(self, error):
        if isinstance(error, ApiError) and error.status == 401: self.session_expired.emit()
        else: self.banner.show_state(str(error))
