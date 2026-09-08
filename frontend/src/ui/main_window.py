from PyQt6.QtCore import Qt, QThreadPool, QTimer
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow,
                             QMessageBox, QPushButton, QScrollArea, QStackedWidget,
                             QVBoxLayout, QWidget)
from .common import EmptyPage, confirm
from .pages.dashboard import DashboardPage
from .pages.login import LoginPage
from .pages.profile import ProfilePage
from .pages.record import AcademicRecordPage
from .pages.resource import ResourcePage
from ..resources import RESOURCES
from ..workers import ApiWorker


class MainWindow(QMainWindow):
    def __init__(self, api, settings):
        super().__init__(); self.api, self.settings = api, settings; self.pages = {}; self.nav_buttons = {}; self.worker = None
        self.setWindowTitle('Student Information System'); self.resize(1280, 760); self.setMinimumSize(760, 540)
        self.login = LoginPage(api, settings.api_base_url); self.login.authenticated.connect(self._authenticated)
        self.setCentralWidget(self.login); self.statusBar().showMessage('Sign in to continue')

    def _authenticated(self, user):
        self._build_shell(user); self.statusBar().showMessage(f"Signed in as {user['name']} · {user['role']}", 5000)

    def _build_shell(self, user):
        role = user['role']; shell = QWidget(); layout = QHBoxLayout(shell); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(218); side = QVBoxLayout(sidebar); side.setContentsMargins(12, 22, 12, 16)
        brand = QLabel('SIS\nACADEMIC PORTAL'); brand.setWordWrap(True); brand.setStyleSheet('font-size:13pt;font-weight:800;padding:8px;'); side.addWidget(brand)
        user_label = QLabel(f"{user['name']}\n{role.title()}"); user_label.setWordWrap(True); user_label.setStyleSheet('padding:8px;color:#a5b4fc;'); side.addWidget(user_label)
        self.stack = QStackedWidget(); self.pages = {}
        dashboard = DashboardPage(self.api, role); dashboard.navigate.connect(self.navigate); self._wire(dashboard); self.pages['dashboard'] = dashboard
        keys = {
            'ADMIN': ['users', 'students', 'programs', 'courses', 'academic-terms', 'course-offerings', 'enrollments', 'grades'],
            'REGISTRAR': ['students', 'programs', 'courses', 'academic-terms', 'course-offerings', 'enrollments', 'grades'],
            'INSTRUCTOR': ['course-offerings', 'enrollments', 'grades'],
            'STUDENT': ['programs', 'courses', 'academic-terms'],
        }[role]
        for key in keys:
            page = ResourcePage(self.api, RESOURCES[key], role); self._wire(page)
            page.academic_record_requested.connect(self.open_record); self.pages[key] = page
        if role == 'STUDENT': self.pages['records'] = AcademicRecordPage(self.api)
        self.pages['profile'] = ProfilePage(user, self.settings.api_base_url)
        for page in self.pages.values(): self.stack.addWidget(page)
        labels = {'dashboard': 'Overview', 'users': 'Users & Roles', 'students': 'Students', 'programs': 'Programs', 'courses': 'Courses',
                  'academic-terms': 'Academic Terms', 'course-offerings': 'Course Offerings', 'enrollments': 'Enrollments',
                  'grades': 'Grades', 'records': 'My Academic Record', 'profile': 'Profile & Connection'}
        self.nav_buttons = {}
        for key in self.pages:
            button = QPushButton(labels[key].replace('&', '&&')); button.setToolTip(labels[key]); button.setAccessibleName(labels[key]); button.setObjectName('nav'); button.setCheckable(True)
            button.clicked.connect(lambda _, route=key: self.navigate(route)); side.addWidget(button); self.nav_buttons[key] = button
        side.addStretch(); logout = QPushButton('Sign out'); logout.setObjectName('nav'); logout.clicked.connect(self.logout); side.addWidget(logout)
        layout.addWidget(sidebar); layout.addWidget(self.stack, 1); self.setCentralWidget(shell); self.navigate('dashboard')

    def _wire(self, page):
        if hasattr(page, 'session_expired'): page.session_expired.connect(self.session_expired)

    def navigate(self, route):
        if not self.api.authenticated:
            self.session_expired(); return
        page = self.pages.get(route)
        if page is None:
            page = EmptyPage('Page not found', 'The requested application view does not exist.')
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        for key, button in self.nav_buttons.items(): button.setChecked(key == route)

    def open_record(self, student_id):
        page = AcademicRecordPage(self.api, student_id); self._wire(page); self.stack.addWidget(page); self.stack.setCurrentWidget(page)

    def logout(self):
        if not confirm(self, 'Sign out', 'End this authenticated session?'): return
        self.setEnabled(False); self.worker = ApiWorker(self.api.logout)
        self.worker.signals.error.connect(lambda _: None)
        self.worker.signals.finished.connect(lambda: (self.setEnabled(True), self._show_login('You have signed out.')))
        QThreadPool.globalInstance().start(self.worker)

    def session_expired(self): self._show_login('Your session expired or is invalid. Please sign in again.')

    def _show_login(self, message):
        self.api.clear_auth(); self.login = LoginPage(self.api, self.settings.api_base_url); self.login.authenticated.connect(self._authenticated)
        self.setCentralWidget(self.login); self.login.reset(message); self.statusBar().showMessage('Authentication required')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        central = self.centralWidget()
        if central and central.layout() and central.layout().count() >= 2:
            sidebar = central.layout().itemAt(0).widget()
            if sidebar: sidebar.setFixedWidth(196 if self.width() < 900 else 218)
