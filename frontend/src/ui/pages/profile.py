from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QFrame, QLabel, QVBoxLayout, QWidget
from ..common import title_block


class ProfilePage(QWidget):
    def __init__(self, user, api_url):
        super().__init__(); layout = QVBoxLayout(self); layout.setContentsMargins(24, 20, 24, 20)
        layout.addLayout(title_block('Profile & Connection', 'Current authenticated identity and frontend configuration.'))
        card = QFrame(); card.setObjectName('card'); form = QFormLayout(card); form.setContentsMargins(24, 24, 24, 24)
        fields = [('Name', user.get('name')), ('Email', user.get('email')), ('Role', user.get('role')),
                  ('Account status', 'Active' if user.get('is_active') else 'Inactive'), ('API base URL', api_url),
                  ('Authentication state', 'Token held in application memory; cleared on logout or 401')]
        for title, value in fields:
            label = QLabel(str(value)); label.setWordWrap(True); label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); form.addRow(title, label)
        layout.addWidget(card); layout.addStretch()
