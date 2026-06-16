"""PySide6 tray application lifecycle for ChaseOS."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from chaseos.app.app_state import AppState
from chaseos.app.command_router import CommandResult, CommandRouter, TerminalLine
from chaseos.app.terminal_window import TerminalWindow


def create_fallback_icon() -> QIcon:
    """Create a simple local tray icon when no asset exists yet."""

    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor("#202020"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#b08a2e"))
    painter.setBrush(QColor("#2a2a2a"))
    painter.drawRoundedRect(8, 8, 48, 48, 8, 8)
    painter.setPen(QColor("#b08a2e"))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(24)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "C")
    painter.end()

    return QIcon(pixmap)


class ChaseOSTrayApp:
    """Owns the terminal window, command router, and Windows tray icon."""

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.state = AppState()
        self.router = CommandRouter()
        self.window = TerminalWindow(self.state)
        self.tray = QSystemTrayIcon(create_fallback_icon(), self.app)
        self.tray.setToolTip("ChaseOS")
        self.tray.activated.connect(self._handle_tray_activation)
        self.tray.setContextMenu(self._build_tray_menu())

        self.window.command_submitted.connect(self.handle_command)
        self.window.hide_requested.connect(self.hide_window)
        self.header_timer = QTimer(self.app)
        self.header_timer.setInterval(1000)
        self.header_timer.timeout.connect(self.window.refresh_status)
        self.header_timer.start()

    def start(self) -> int:
        QApplication.setQuitOnLastWindowClosed(False)
        self.tray.show()
        self.show_window()
        return self.app.exec()

    def _build_tray_menu(self) -> QMenu:
        menu = QMenu()
        self._add_menu_action(
            menu,
            "Start 15-Minute Sequence",
            lambda: self._run_menu_command("/start"),
        )
        self._add_menu_action(menu, "Quick Theme Shift", lambda: self._run_menu_command("/theme"))
        self._add_menu_action(
            menu,
            "Today's Public Poster",
            lambda: self._run_menu_command("/poster"),
        )
        self._add_menu_action(
            menu,
            "Regenerate Wallpapers",
            lambda: self._run_menu_command("/regenerate"),
        )
        self._add_menu_action(
            menu,
            "Open Poster Archive",
            lambda: self._show_placeholder("poster archive placeholder ready."),
        )
        self._add_menu_action(
            menu,
            "Settings",
            lambda: self._show_placeholder("settings placeholder ready."),
        )
        self._add_menu_action(menu, "Reset Desktop", lambda: self._run_menu_command("/reset"))
        menu.addSeparator()
        self._add_menu_action(menu, "Exit", self.exit_app)
        return menu

    def _add_menu_action(self, menu: QMenu, label: str, callback: Callable[[], None]) -> QAction:
        action = QAction(label, menu)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_window()

    def _run_menu_command(self, command: str) -> None:
        self.show_window()
        self.handle_command(command)

    def _show_placeholder(self, message: str) -> None:
        self.show_window()
        self.window.append_line(TerminalLine("system", message))

    def handle_command(self, raw_input: str) -> None:
        raw_input = raw_input.strip()
        result = self.router.route(raw_input)
        if result.is_noop:
            return

        self.window.append_user_input(raw_input)
        self._apply_input_result(raw_input, result)

    def _apply_input_result(self, raw_input: str, result: CommandResult) -> None:
        if result.action == "clear":
            self.window.clear_output()
            return

        if result.action == "exit":
            self.window.append_lines(result.lines)
            QTimer.singleShot(100, self.exit_app)
            return

        if result.command in {"/help", "/monitors"}:
            self.window.append_lines(result.lines)
            return

        response = self.state.sequence.handle_input(raw_input, result)
        self.window.append_lines(response.lines)
        self.window.refresh_status()

    def show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self.window.focus_command_input()

    def hide_window(self) -> None:
        self.window.hide()

    def toggle_window(self) -> None:
        if self.window.isVisible():
            self.hide_window()
        else:
            self.show_window()

    def exit_app(self) -> None:
        self.tray.hide()
        self.app.quit()


def run(argv: Sequence[str] | None = None) -> int:
    """Run the ChaseOS tray shell."""

    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("ChaseOS")
    app.setQuitOnLastWindowClosed(False)
    tray_app = ChaseOSTrayApp(app)
    return tray_app.start()
