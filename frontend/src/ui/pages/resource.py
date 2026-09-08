from PyQt6.QtCore import Qt, QThreadPool, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QBoxLayout)
from ...api.client import ApiError
from ...workers import ApiWorker
from ...resources import display_for
from ..common import BusyBar, StateBanner, confirm, title_block
from ..dialogs import DetailDialog, ResourceDialog


class ResourcePage(QWidget):
    session_expired = pyqtSignal()
    academic_record_requested = pyqtSignal(int)

    def __init__(self, api, spec, role):
        super().__init__(); self.api, self.spec, self.role = api, spec, role
        self.page = 1; self.last_page = 1; self.rows = []; self.worker = None; self.workers = []; self.lookup_labels = {}; self.generation = 0
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(12)
        self.banner = StateBanner()
        top = QHBoxLayout(); top.addLayout(title_block(spec.title, 'Live data from the configured REST API.'), 1)
        self.add_button = QPushButton('Add ' + spec.title.rstrip('s')); self.add_button.setObjectName('primary'); self.add_button.clicked.connect(self.create)
        self.add_button.setVisible(role in spec.write_roles)
        top.addWidget(self.add_button); layout.addLayout(top)
        controls = QFrame(); controls.setObjectName('card'); self.control_layout = QHBoxLayout(controls)
        self.search = QLineEdit(); self.search.setPlaceholderText('Search…'); self.search.setClearButtonEnabled(True); self.search.setAccessibleName('Search records')
        self.search.setVisible(spec.search); self.control_layout.addWidget(self.search, 2)
        self.filter_widgets = {}
        for key, label, options in spec.filters:
            if options is None:
                widget = QLineEdit(); widget.setPlaceholderText(label)
            else:
                widget = QComboBox()
                if isinstance(options, str):
                    widget.addItem('Loading ' + label.lower() + '…', ''); widget.setEnabled(False)
                    worker = ApiWorker(self.api.list, options, per_page=100)
                    worker.signals.result.connect(lambda data, w=widget, l=label, endpoint=options, field=key: self._fill_filter(w, l, endpoint, field, data['results']))
                    worker.signals.error.connect(lambda error, w=widget: (w.clear(), w.addItem('Unavailable', ''), self.banner.show_state(str(error))))
                    self.workers.append(worker); QThreadPool.globalInstance().start(worker)
                else:
                    widget.addItem('All ' + label.lower(), '')
                    for option in options:
                        value, text = option if isinstance(option, tuple) else (option, option)
                        widget.addItem(str(text), value)
            widget.setAccessibleName(label + ' filter'); self.filter_widgets[key] = widget; self.control_layout.addWidget(widget, 1)
        self.sort = QComboBox(); self.sort.addItem('Default order', '')
        for value, label in spec.sorts:
            self.sort.addItem(label + ' ↑', value); self.sort.addItem(label + ' ↓', '-' + value)
        self.sort.setAccessibleName('Sort records'); self.control_layout.addWidget(self.sort)
        refresh = QPushButton('Refresh'); refresh.clicked.connect(self.refresh); self.control_layout.addWidget(refresh)
        layout.addWidget(controls)
        self.busy = BusyBar(); layout.addWidget(self.busy)
        self.banner.retry.clicked.connect(self.refresh); layout.addWidget(self.banner)
        self.table = QTableWidget(0, len(spec.columns)); self.table.setHorizontalHeaderLabels([label for _, label in spec.columns])
        self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.view); layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.state = QLabel('Ready'); self.state.setObjectName('muted'); actions.addWidget(self.state, 1)
        self.record_button = QPushButton('Academic record'); self.record_button.clicked.connect(self.academic_record); self.record_button.setVisible(spec.key == 'students')
        self.view_button = QPushButton('View'); self.view_button.clicked.connect(self.view)
        self.edit_button = QPushButton('Edit'); self.edit_button.clicked.connect(self.edit); self.edit_button.setVisible(role in spec.write_roles)
        self.delete_button = QPushButton('Deactivate' if spec.key == 'students' else 'Delete'); self.delete_button.setObjectName('danger'); self.delete_button.clicked.connect(self.remove); self.delete_button.setVisible(role in spec.write_roles and spec.delete)
        for button in [self.record_button, self.view_button, self.edit_button, self.delete_button]: actions.addWidget(button)
        self.previous = QPushButton('Previous'); self.previous.clicked.connect(lambda: self.change_page(-1)); actions.addWidget(self.previous)
        self.page_label = QLabel('Page 1 of 1'); actions.addWidget(self.page_label)
        self.next = QPushButton('Next'); self.next.clicked.connect(lambda: self.change_page(1)); actions.addWidget(self.next)
        layout.addLayout(actions)
        self.search.returnPressed.connect(self._reset_refresh)
        self.sort.currentIndexChanged.connect(self._reset_refresh)
        for widget in self.filter_widgets.values():
            (widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.returnPressed).connect(self._reset_refresh)

    def _fill_filter(self, widget, label, endpoint, field, rows):
        widget.blockSignals(True); widget.clear(); widget.addItem('All ' + label.lower(), '')
        self.lookup_labels[field] = {row['id']: display_for(endpoint, row) for row in rows}
        for row in rows: widget.addItem(self.lookup_labels[field][row['id']], row['id'])
        widget.setEnabled(True); widget.blockSignals(False)
        if self.rows: self._render_rows()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.rows: self.refresh()

    def _reset_refresh(self, *args): self.page = 1; self.refresh()

    def params(self):
        params = {'page': self.page, 'per_page': 20, 'search': self.search.text().strip(), 'sort': self.sort.currentData()}
        for key, widget in self.filter_widgets.items():
            params[key] = widget.currentData() if isinstance(widget, QComboBox) else widget.text().strip()
        return params

    def refresh(self):
        self.generation += 1; generation = self.generation
        self.banner.hide(); self.busy.show(); self.state.setText('Loading from API…')
        self.worker = ApiWorker(self.api.list, self.spec.path, **self.params())
        self.worker.signals.result.connect(lambda data: self._loaded(data) if generation == self.generation else None)
        self.worker.signals.error.connect(lambda error: self._error(error) if generation == self.generation else None)
        self.worker.signals.finished.connect(lambda: self.busy.hide() if generation == self.generation else None)
        QThreadPool.globalInstance().start(self.worker)

    def _loaded(self, data):
        self.rows = data.get('results', []); self.page = data.get('page', 1); self.last_page = data.get('last_page', 1)
        self._render_rows()
        self.page_label.setText(f'Page {self.page} of {self.last_page}')
        self.previous.setEnabled(self.page > 1); self.next.setEnabled(self.page < self.last_page)
        count = data.get('count', len(self.rows)); self.state.setText(f'{count} record(s)' if count else 'No records match these controls.')
        if not self.rows: self.banner.show_state('No records found. Adjust the search or filters, or create the first record.', False)

    def _render_rows(self):
        self.table.setRowCount(len(self.rows))
        for row_index, row in enumerate(self.rows):
            for column, (key, _) in enumerate(self.spec.columns):
                value = row.get(key, '—')
                value = self.lookup_labels.get(key, {}).get(value, value)
                item = QTableWidgetItem('—' if value in ('', None) else str(value))
                item.setData(Qt.ItemDataRole.UserRole, row.get('id')); self.table.setItem(row_index, column, item)
        self.table.resizeColumnsToContents(); self.page_label.setText(f'Page {self.page} of {self.last_page}')

    def _error(self, error):
        if isinstance(error, ApiError) and error.status == 401: self.session_expired.emit(); return
        prefix = 'Access denied. ' if isinstance(error, ApiError) and error.status == 403 else ''
        self.banner.show_state(prefix + str(error)); self.state.setText('Could not load records')

    def selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            QMessageBox.information(self, 'Select a record', 'Select a table row first.'); return None
        return self.rows[row]

    def view(self, *_):
        if record := self.selected(): DetailDialog(self.spec.title.rstrip('s') + ' details', record, self).exec()

    def create(self): self._form(None)
    def edit(self):
        if record := self.selected(): self._form(record)

    def _form(self, record):
        dialog = ResourceDialog(self.api, self.spec, record, self)
        def submit(payload):
            fn = self.api.update if record else self.api.create
            args = (self.spec.path, record['id'], payload) if record else (self.spec.path, payload)
            self.worker = ApiWorker(fn, *args)
            self.worker.signals.result.connect(lambda _: (dialog.accept(), self._mutation_done('Record saved successfully.')))
            self.worker.signals.error.connect(lambda error: (dialog.buttons.setEnabled(True), dialog.show_api_error(error)))
            QThreadPool.globalInstance().start(self.worker)
        dialog.submit_requested.connect(submit)
        dialog.exec()

    def remove(self):
        record = self.selected()
        if not record: return
        if self.spec.key == 'students':
            if not confirm(self, 'Deactivate student', 'Deactivate this student? Historical records will be preserved.'): return
            fn, args, message = self.api.update, (self.spec.path, record['id'], {'status': 'INACTIVE'}), 'Student deactivated.'
        else:
            if not confirm(self, 'Delete record', 'Permanently delete this unreferenced record? This cannot be undone.'): return
            fn, args, message = self.api.delete, (self.spec.path, record['id']), 'Record deleted.'
        self.busy.show(); self.worker = ApiWorker(fn, *args)
        self.worker.signals.result.connect(lambda _: self._mutation_done(message))
        self.worker.signals.error.connect(lambda error: self._mutation_error(error))
        self.worker.signals.finished.connect(self.busy.hide); QThreadPool.globalInstance().start(self.worker)

    def _mutation_done(self, message):
        self.state.setText(message); self.refresh()

    def _mutation_error(self, error):
        self.banner.show_state(str(error)); QMessageBox.warning(self, 'Action failed', str(error))

    def academic_record(self):
        if record := self.selected(): self.academic_record_requested.emit(record['id'])

    def change_page(self, delta):
        target = self.page + delta
        if 1 <= target <= self.last_page: self.page = target; self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        narrow = self.width() < 760
        self.control_layout.setDirection(QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight)
        self.state.setVisible(not narrow)
        self.view_button.setVisible(not narrow)
