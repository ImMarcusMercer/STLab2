APP_STYLE = r'''
* { font-family: "Segoe UI"; font-size: 10pt; color: #172033; }
QMainWindow, QWidget { background: #f5f7fb; }
QFrame#sidebar { background: #172554; border: none; }
QFrame#sidebar QLabel { color: #e0e7ff; background: transparent; }
QPushButton#nav { color: #c7d2fe; background: transparent; border: none; text-align: left;
                  padding: 11px 16px; border-radius: 7px; }
QPushButton#nav:hover { background: #263a78; color: white; }
QPushButton#nav:checked { background: #3b82f6; color: white; font-weight: 600; }
QFrame#card, QGroupBox { background: white; border: 1px solid #dbe2ef; border-radius: 10px; }
QGroupBox { margin-top: 12px; padding-top: 12px; font-weight: 600; }
QLabel#pageTitle { font-size: 20pt; font-weight: 700; color: #111827; }
QLabel#eyebrow { color: #2563eb; font-size: 9pt; font-weight: 700; }
QLabel#muted { color: #667085; }
QLabel#metric { font-size: 24pt; font-weight: 700; color: #1d4ed8; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {
  background: white; border: 1px solid #cbd5e1; border-radius: 7px; padding: 7px;
  selection-background-color: #2563eb;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus,
QTextEdit:focus { border: 2px solid #3b82f6; }
QPushButton { background: #e8eef9; border: none; border-radius: 7px; padding: 8px 13px; font-weight: 600; }
QPushButton:hover { background: #dce6f7; }
QPushButton:disabled { color: #94a3b8; background: #eef2f7; }
QPushButton#primary { background: #2563eb; color: white; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#danger { background: #fee2e2; color: #b91c1c; }
QTableWidget { background: white; alternate-background-color: #f8fafc; border: 1px solid #dbe2ef;
               border-radius: 8px; gridline-color: #e5e7eb; }
QHeaderView::section { background: #eef2ff; color: #334155; padding: 8px; border: none;
                       border-bottom: 1px solid #cbd5e1; font-weight: 600; }
QToolTip { background: #172554; color: white; border: none; padding: 4px; }
QProgressBar { border: none; background: #e2e8f0; height: 4px; }
QProgressBar::chunk { background: #3b82f6; }
QStatusBar { background: white; border-top: 1px solid #dbe2ef; }
'''
