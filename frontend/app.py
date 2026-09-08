import sys
from PyQt6.QtWidgets import QApplication
from src.config import Settings
from src.api.client import ApiClient
from src.ui.main_window import MainWindow
from src.ui.theme import APP_STYLE


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Student Information System')
    app.setStyle('Fusion')
    app.setStyleSheet(APP_STYLE)
    settings = Settings.load()
    window = MainWindow(ApiClient(settings.api_base_url, settings.timeout_seconds), settings)
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
