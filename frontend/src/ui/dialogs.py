from PyQt6.QtCore import QDate, Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFormLayout, QLabel, QLineEdit,
                             QSpinBox, QTextEdit, QVBoxLayout)
from ..resources import display_for
from ..workers import ApiWorker
from ..api.client import ApiError


class ResourceDialog(QDialog):
    submit_requested = pyqtSignal(dict)
    def __init__(self, api, spec, record=None, parent=None):
        super().__init__(parent)
        self.api, self.spec, self.record = api, spec, record or {}
        self.setWindowTitle(('Edit ' if record else 'Create ') + spec.title.rstrip('s'))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        intro = QLabel('Required fields are marked with *. Backend validation remains authoritative.')
        intro.setObjectName('muted')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.form = QFormLayout()
        self.widgets, self.errors, self.workers = {}, {}, []
        self.general_error = QLabel()
        self.general_error.setStyleSheet('color:#b91c1c;')
        self.general_error.setWordWrap(True)
        for field in spec.fields:
            widget = self._widget(field)
            self.widgets[field.key] = widget
            error = QLabel()
            error.setStyleSheet('color:#b91c1c; font-size:9pt;')
            error.setWordWrap(True)
            self.errors[field.key] = error
            field_box = QVBoxLayout()
            field_box.setContentsMargins(0, 0, 0, 0)
            field_box.addWidget(widget)
            field_box.addWidget(error)
            required = field.required and not (record and field.key == 'password')
            self.form.addRow(field.label + (' *' if required else ''), field_box)
        layout.addLayout(self.form)
        layout.addWidget(self.general_error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                        QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self._validate_then_submit)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._set_values()

    def _widget(self, field):
        if field.kind in ('choice',) or (field.kind == 'int' and field.choices):
            widget = QComboBox()
            if not field.required:
                widget.addItem('— Not specified —', None)
            for value, label in field.choices:
                widget.addItem(label, int(value) if field.kind == 'int' else value)
            return widget
        if field.kind == 'ref':
            widget = QComboBox()
            widget.addItem('Loading…', None)
            widget.setEnabled(False)
            worker = ApiWorker(self._load_reference, field.reference)
            worker.signals.result.connect(lambda rows, w=widget, f=field: self._fill_reference(w, f, rows))
            worker.signals.error.connect(lambda exc, w=widget: self._reference_error(w, exc))
            self.workers.append(worker)
            QThreadPool.globalInstance().start(worker)
            return widget
        if field.kind == 'int':
            widget = QSpinBox(); widget.setRange(0, 1_000_000)
            return widget
        if field.kind == 'decimal':
            widget = QDoubleSpinBox(); widget.setRange(0, 1000); widget.setDecimals(2)
            return widget
        if field.kind == 'date':
            widget = QDateEdit(); widget.setCalendarPopup(True); widget.setDisplayFormat('yyyy-MM-dd')
            widget.setSpecialValueText('Not specified'); widget.setMinimumDate(QDate(1900, 1, 1)); widget.setDate(widget.minimumDate())
            return widget
        if field.kind == 'multiline':
            widget = QTextEdit(); widget.setMaximumHeight(80)
            return widget
        widget = QLineEdit()
        if field.kind == 'password':
            widget.setEchoMode(QLineEdit.EchoMode.Password)
        if field.kind == 'email':
            widget.setPlaceholderText('name@example.com')
        return widget

    def _load_reference(self, endpoint):
        if '?' in endpoint:
            path, query = endpoint.split('?', 1)
            params = dict(part.split('=', 1) for part in query.split('&'))
        else:
            path, params = endpoint, {}
        return self.api.list(path, per_page=100, **params)['results']

    def _fill_reference(self, widget, field, rows):
        current = self.record.get(field.key)
        widget.clear()
        if not field.required:
            widget.addItem('— Not specified —', None)
        for row in rows:
            widget.addItem(display_for(field.reference, row), row['id'])
        widget.setEnabled(True)
        index = widget.findData(current)
        if index >= 0:
            widget.setCurrentIndex(index)

    def _reference_error(self, widget, exc):
        widget.clear(); widget.addItem('Reference data unavailable', None)
        self.general_error.setText(str(exc))

    def _set_values(self):
        for field in self.spec.fields:
            if field.key not in self.record or field.kind == 'ref':
                continue
            value, widget = self.record[field.key], self.widgets[field.key]
            if isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index >= 0: widget.setCurrentIndex(index)
            elif isinstance(widget, QDateEdit):
                parsed = QDate.fromString(str(value), 'yyyy-MM-dd')
                if parsed.isValid(): widget.setDate(parsed)
            elif isinstance(widget, QSpinBox): widget.setValue(int(value or 0))
            elif isinstance(widget, QDoubleSpinBox): widget.setValue(float(value or 0))
            elif isinstance(widget, QTextEdit): widget.setPlainText(str(value or ''))
            else: widget.setText(str(value or ''))

    def payload(self):
        data = {}
        for field in self.spec.fields:
            widget = self.widgets[field.key]
            if isinstance(widget, QComboBox): value = widget.currentData()
            elif isinstance(widget, QDateEdit): value = None if widget.date() == widget.minimumDate() else widget.date().toString('yyyy-MM-dd')
            elif isinstance(widget, QSpinBox): value = widget.value()
            elif isinstance(widget, QDoubleSpinBox): value = f'{widget.value():.2f}'
            elif isinstance(widget, QTextEdit): value = widget.toPlainText().strip()
            else: value = widget.text().strip()
            if value not in ('', None) or field.required:
                data[field.key] = value
        return data

    def _validate_then_submit(self):
        valid = True
        for field in self.spec.fields:
            self.errors[field.key].clear()
            value = self.payload().get(field.key)
            if field.required and not (self.record and field.key == 'password') and value in ('', None, 0):
                self.errors[field.key].setText('This field is required.')
                valid = False
            if field.kind == 'email' and value and ('@' not in value or value.startswith('@') or value.endswith('@')):
                self.errors[field.key].setText('Enter a valid email address.')
                valid = False
        if valid:
            self.buttons.setEnabled(False)
            self.general_error.setText('Saving through the API…')
            self.submit_requested.emit(self.payload())

    def show_api_error(self, error):
        self.general_error.setText(error.message)
        for field, message in error.field_messages.items():
            key = field
            if key not in self.errors and key.endswith('_id'):
                key = key
            if key in self.errors:
                self.errors[key].setText(message)


class DetailDialog(QDialog):
    def __init__(self, title, record, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title); self.setMinimumWidth(480)
        form = QFormLayout(self)
        for key, value in record.items():
            if key not in ('created_at', 'updated_at'):
                label = QLabel(str(value if value not in (None, '') else '—'))
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                label.setWordWrap(True)
                form.addRow(key.replace('_', ' ').title(), label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
