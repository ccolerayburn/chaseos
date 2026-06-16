"""Terminal-style dark command window for ChaseOS."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from chaseos.app.app_state import AppState
from chaseos.app.command_router import TerminalLine

BACKGROUND = "#202020"
SURFACE = "#242424"
BORDER = "#36332a"
AMBER = "#b08a2e"
AMBER_DIM = "#8f732b"
SELECTION = "#3a3324"


def select_terminal_font(point_size: int = 10) -> QFont:
    """Choose a calm monospace font, preferring Cascadia Mono when available."""

    available = set(QFontDatabase.families())
    for family in ("Cascadia Mono", "Cascadia Code", "Consolas", "Courier New"):
        if family in available:
            return QFont(family, point_size)
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPointSize(point_size)
    return font


class TerminalWindow(QMainWindow):
    """Resizable terminal shell with a single command input line."""

    command_submitted = Signal(str)
    hide_requested = Signal()

    def __init__(self, state: AppState | None = None) -> None:
        super().__init__()
        self.state = state or AppState()
        self.terminal_font = select_terminal_font()

        self.setWindowTitle("ChaseOS")
        self.resize(720, 520)
        self.setMinimumSize(560, 380)

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        self.title_label = QLabel("CHASEOS :: START SEQUENCE", root)
        self.title_label.setFont(select_terminal_font(11))
        self.status_label = QLabel(self.state.header_status, root)
        self.status_label.setFont(select_terminal_font(9))

        header = QVBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(2)
        header.addWidget(self.title_label)
        header.addWidget(self.status_label)
        layout.addLayout(header)

        self.output = QPlainTextEdit(root)
        self.output.setReadOnly(True)
        self.output.setFont(self.terminal_font)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.output, stretch=1)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        prompt = QLabel(">", root)
        prompt.setFont(self.terminal_font)
        self.input = QLineEdit(root)
        self.input.setFont(self.terminal_font)
        self.input.setPlaceholderText("type a command")
        self.input.returnPressed.connect(self._submit_current_input)

        input_row.addWidget(prompt)
        input_row.addWidget(self.input, stretch=1)
        layout.addLayout(input_row)

        self.setCentralWidget(root)
        self._apply_style()
        self._install_shortcuts()
        self.write_initial_output()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {BACKGROUND};
                color: {AMBER};
            }}
            QLabel {{
                color: {AMBER};
                letter-spacing: 0px;
            }}
            QPlainTextEdit {{
                background: {SURFACE};
                color: {AMBER};
                border: 1px solid {BORDER};
                padding: 8px;
                selection-background-color: {SELECTION};
                selection-color: {AMBER};
            }}
            QLineEdit {{
                background: {BACKGROUND};
                color: {AMBER};
                border: 1px solid {BORDER};
                padding: 7px 8px;
                selection-background-color: {SELECTION};
                selection-color: {AMBER};
            }}
            QLineEdit:focus {{
                border-color: {AMBER_DIM};
            }}
            """
        )

    def _install_shortcuts(self) -> None:
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_output)

    def write_initial_output(self) -> None:
        self.append_lines(
            (
                TerminalLine("chaseos", "ready."),
                TerminalLine("chaseos", "type /start to begin."),
                TerminalLine("chaseos", "type /help for commands."),
            )
        )

    def refresh_status(self) -> None:
        self.status_label.setText(self.state.header_status)

    def append_line(self, line: TerminalLine) -> None:
        self.output.appendPlainText(line.render())
        self._scroll_to_bottom()

    def append_lines(self, lines: tuple[TerminalLine, ...]) -> None:
        for line in lines:
            self.append_line(line)

    def append_user_input(self, raw_input: str) -> None:
        self.append_line(TerminalLine("user", raw_input.strip()))

    def append_system_message(self, message: str) -> None:
        self.append_line(TerminalLine("system", message))

    def clear_output(self) -> None:
        self.output.clear()

    def focus_command_input(self) -> None:
        self.input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _submit_current_input(self) -> None:
        raw_input = self.input.text()
        self.input.clear()
        self.command_submitted.emit(raw_input)

    def _scroll_to_bottom(self) -> None:
        scrollbar = self.output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)
