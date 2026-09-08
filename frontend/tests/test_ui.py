from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton
import time
from src.config import Settings
from src.api.client import ApiClient, ApiError
from src.resources import RESOURCES
from src.ui.dialogs import ResourceDialog
from src.ui.main_window import MainWindow
from src.ui.pages.login import LoginPage
from src.ui.pages.resource import ResourcePage


class StubApi(ApiClient):
    def __init__(self): super().__init__('http://127.0.0.1:8000/api/v1'); self.calls = []
    def list(self, resource, **params):
        self.calls.append((resource, params))
        if resource == 'programs':
            return {'count': 1, 'page': 1, 'per_page': 100, 'last_page': 1, 'next': None, 'previous': None,
                    'results': [{'id': 1, 'code': 'BSIT', 'name': 'Information Technology'}]}
        return {'count': 1, 'page': 1, 'per_page': 20, 'last_page': 1, 'next': None, 'previous': None,
                'results': [{'id': 7, 'student_number': '2026-00007', 'first_name': 'Ana',
                             'last_name': 'Santos', 'program_id': 1, 'year_level': 3, 'status': 'ACTIVE'}]}


def test_login_validates_before_network_request(qtbot):
    api = StubApi(); page = LoginPage(api, api.base_url); qtbot.addWidget(page); page.show()
    qtbot.mouseClick(page.submit, Qt.MouseButton.LeftButton)
    assert page.error.isVisible()
    assert 'valid email' in page.error.text()


def test_student_form_requires_minimum_fields(qtbot):
    dialog = ResourceDialog(StubApi(), RESOURCES['students']); qtbot.addWidget(dialog); dialog.show()
    qtbot.mouseClick(dialog.buttons.button(dialog.buttons.StandardButton.Save), Qt.MouseButton.LeftButton)
    assert 'required' in dialog.errors['student_number'].text().lower()
    assert dialog.result() == 0


def test_server_validation_is_mapped_to_correct_form(qtbot):
    dialog = ResourceDialog(StubApi(), RESOURCES['students']); qtbot.addWidget(dialog)
    dialog.show_api_error(ApiError(422, 'Validation failed.', {'student_number': ['Already exists.']}))
    assert dialog.errors['student_number'].text() == 'Already exists.'
    assert dialog.general_error.text() == 'Validation failed.'


def test_resource_list_renders_backend_pagination_and_rows(qtbot):
    api = StubApi(); page = ResourcePage(api, RESOURCES['students'], 'REGISTRAR'); qtbot.addWidget(page)
    page._loaded(api.list('students'))
    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == '2026-00007'
    assert page.page_label.text() == 'Page 1 of 1'
    assert page.state.text() == '1 record(s)'


def test_resource_controls_send_backend_query_parameters(qtbot):
    api = StubApi(); page = ResourcePage(api, RESOURCES['students'], 'REGISTRAR'); qtbot.addWidget(page)
    page.search.setText('Santos'); page.filter_widgets['year_level'].setCurrentIndex(3)
    params = page.params()
    assert params['search'] == 'Santos'
    assert params['year_level'] == '3'
    assert params['page'] == 1 and params['per_page'] == 20


def test_relationship_filter_loads_live_api_labels(qtbot):
    api = StubApi(); page = ResourcePage(api, RESOURCES['students'], 'REGISTRAR'); qtbot.addWidget(page)
    widget = page.filter_widgets['program_id']
    qtbot.waitUntil(widget.isEnabled, timeout=2000)
    assert widget.itemText(1) == 'BSIT - Information Technology'


def test_slow_list_displays_loading_indicator(qtbot):
    class SlowApi(StubApi):
        def list(self, resource, **params):
            time.sleep(.15)
            return super().list(resource, **params)
    page = ResourcePage(SlowApi(), RESOURCES['programs'], 'REGISTRAR'); qtbot.addWidget(page); page.show(); page.refresh()
    assert page.busy.isVisible()
    qtbot.waitUntil(lambda: not page.busy.isVisible(), timeout=3000)


def test_role_navigation_hides_forbidden_modules(qtbot):
    api = StubApi(); api.token = 'token'; api.user = {'id': 1, 'name': 'Student', 'email': 's@example.com', 'role': 'STUDENT', 'is_active': True}
    window = MainWindow(api, Settings(api.base_url, 15)); qtbot.addWidget(window); window._authenticated(api.user)
    assert 'students' not in window.nav_buttons
    assert 'enrollments' not in window.nav_buttons
    assert 'grades' not in window.nav_buttons
    assert 'records' in window.nav_buttons
    assert 'profile' in window.nav_buttons


def test_admin_navigation_contains_every_management_module(qtbot):
    api = StubApi(); api.token = 'token'; api.user = {'id': 1, 'name': 'Admin', 'email': 'a@example.com', 'role': 'ADMIN', 'is_active': True}
    window = MainWindow(api, Settings(api.base_url, 15)); qtbot.addWidget(window); window._authenticated(api.user)
    assert {'users', 'students', 'programs', 'courses', 'academic-terms', 'course-offerings', 'enrollments', 'grades'} <= set(window.nav_buttons)


def test_protected_navigation_returns_to_login_without_session(qtbot):
    api = StubApi(); api.token = 'token'; api.user = {'id': 1, 'name': 'Admin', 'email': 'a@example.com', 'role': 'ADMIN', 'is_active': True}
    window = MainWindow(api, Settings(api.base_url, 15)); qtbot.addWidget(window); window._authenticated(api.user)
    api.clear_auth(); window.navigate('students')
    assert isinstance(window.centralWidget(), LoginPage)
    assert 'session expired' in window.login.error.text().lower()


def test_unknown_route_gets_not_found_state(qtbot):
    api = StubApi(); api.token = 'token'; api.user = {'id': 1, 'name': 'Admin', 'email': 'a@example.com', 'role': 'ADMIN', 'is_active': True}
    window = MainWindow(api, Settings(api.base_url, 15)); qtbot.addWidget(window); window._authenticated(api.user)
    window.navigate('missing-page')
    labels = [label.text() for label in window.stack.currentWidget().findChildren(QLabel)]
    assert 'Page not found' in labels


def test_narrow_window_reduces_sidebar(qtbot):
    api = StubApi(); api.token = 'token'; api.user = {'id': 1, 'name': 'Admin', 'email': 'a@example.com', 'role': 'ADMIN', 'is_active': True}
    window = MainWindow(api, Settings(api.base_url, 15)); qtbot.addWidget(window); window._authenticated(api.user)
    window.resize(800, 600); window.show(); qtbot.wait(10)
    assert window.centralWidget().layout().itemAt(0).widget().width() == 196
