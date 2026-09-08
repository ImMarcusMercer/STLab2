from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
                             QPushButton, QVBoxLayout, QWidget)


def title_block(title, subtitle=''):
    box = QVBoxLayout()
    heading = QLabel(title)
    heading.setObjectName('pageTitle')
    heading.setAccessibleName(title)
    box.addWidget(heading)
    if subtitle:
        label = QLabel(subtitle)
        label.setObjectName('muted')
        label.setWordWrap(True)
        box.addWidget(label)
    return box


class StateBanner(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('card')
        layout = QHBoxLayout(self)
        self.label = QLabel()
        self.label.setWordWrap(True)
        layout.addWidget(self.label, 1)
        self.retry = QPushButton('Retry')
        layout.addWidget(self.retry)
        self.hide()

    def show_state(self, message, retry=True):
        self.label.setText(message)
        self.retry.setVisible(retry)
        self.show()


class BusyBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setRange(0, 0)
        self.setTextVisible(False)
        self.setFixedHeight(4)
        self.hide()


def confirm(parent, title, message):
    return QMessageBox.question(parent, title, message, QMessageBox.StandardButton.Yes |
                                QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes


class EmptyPage(QWidget):
    def __init__(self, title, message):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addStretch()
        heading = QLabel(title)
        heading.setObjectName('pageTitle')
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(message)
        body.setObjectName('muted')
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addStretch()
