"""兼容旧界面的弹窗接口；无 Qt 的 FastAPI 进程改为记录日志。"""
from OAT.utils.logging import QtCore, logger

try:
    from PyQt6.QtWidgets import QMessageBox
except ImportError:
    QMessageBox = None


class PopupWorker(QtCore.QObject):
    show_warning_signal = QtCore.pyqtSignal(str)
    show_error_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.show_warning_signal.connect(self._show_warning)
        self.show_error_signal.connect(self._show_error)
        self.active_popups = []

    def _show_warning(self, message: str):
        if not self._qt_ready():
            logger.warning(message)
            return
        self._show(message, QMessageBox.Icon.Warning, "警告")

    def _show_error(self, message: str):
        if not self._qt_ready():
            logger.error(message)
            return
        self._show(message, QMessageBox.Icon.Critical, "错误")

    @staticmethod
    def _qt_ready():
        if QMessageBox is None:
            return False
        from PyQt6.QtCore import QCoreApplication
        return QCoreApplication.instance() is not None

    def _show(self, message, icon, title):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.finished.connect(lambda: self._remove_popup(msg_box))
        msg_box.show()
        self.active_popups.append(msg_box)

    def _remove_popup(self, popup):
        if popup in self.active_popups:
            self.active_popups.remove(popup)


popup_worker = PopupWorker()


def warning_box(message: str):
    popup_worker.show_warning_signal.emit(str(message))
