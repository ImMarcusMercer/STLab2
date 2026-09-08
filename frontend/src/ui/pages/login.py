from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QWidget)
from ...workers import ApiWorker
from ..common import BusyBar


class LoginPage(QWidget):
    authenticated = pyqtSignal(dict)

    def __init__(self, api, api_url):
        super().__init__(); self.api = api; self.worker = None
        outer = QHBoxLayout(self); outer.setContentsMargins(32, 32, 32, 32)
        outer.addStretch()
        card = QFrame(); card.setObjectName('card'); card.setMaximumWidth(460); card.setMinimumWidth(360)
        layout = QVBoxLayout(card); layout.setContentsMargins(38, 38, 38, 38); layout.setSpacing(14)
        eyebrow = QLabel('STUDENT INFORMATION SYSTEM'); eyebrow.setObjectName('eyebrow')
        heading = QLabel('Welcome back'); heading.setObjectName('pageTitle')
        subtitle = QLabel('Sign in with an account from the REST API.'); subtitle.setObjectName('muted')
        self.email = QLineEdit(); self.email.setPlaceholderText('Email address'); self.email.setAccessibleName('Email address')
        self.password = QLineEdit(); self.password.setPlaceholderText('Password'); self.password.setEchoMode(QLineEdit.EchoMode.Password); self.password.setAccessibleName('Password')
        self.error = QLabel(); self.error.setStyleSheet('color:#b91c1c;'); self.error.setWordWrap(True); self.error.hide()
        self.busy = BusyBar()
        self.submit = QPushButton('Sign in'); self.submit.setObjectName('primary'); self.submit.setDefault(True)
        self.submit.clicked.connect(self.login); self.password.returnPressed.connect(self.login)
        api_label = QLabel(f'API: {api_url}'); api_label.setObjectName('muted'); api_label.setWordWrap(True); api_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        for widget in [eyebrow, heading, subtitle, self.email, self.password, self.error, self.busy, self.submit, api_label]: layout.addWidget(widget)
        outer.addWidget(card); outer.addStretch()

    def login(self):
        email, password = self.email.text().strip(), self.password.text()
        self.error.hide()
        if not email or '@' not in email:
            self.error.setText('Enter a valid email address.'); self.error.show(); self.email.setFocus(); return
        if not password:
            self.error.setText('Password is required.'); self.error.show(); self.password.setFocus(); return
        self.submit.setEnabled(False); self.busy.show()
        self.worker = ApiWorker(self.api.login, email, password)
        self.worker.signals.result.connect(self._success)
        self.worker.signals.error.connect(self._error)
        self.worker.signals.finished.connect(lambda: (self.submit.setEnabled(True), self.busy.hide()))
        QThreadPool.globalInstance().start(self.worker)

    def _success(self, user):
        self.password.clear(); self.authenticated.emit(user)

    def _error(self, error):
        self.error.setText(str(error)); self.error.show()

    def reset(self, message=''):
        self.password.clear()
        if message: self.error.setText(message); self.error.show()
        self.email.setFocus()
