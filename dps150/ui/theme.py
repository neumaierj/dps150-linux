"""Color palette and app stylesheet modeled on the DPS-150's own screen:

near-black background, navy panels with light-blue borders, yellow voltage,
cyan current, green power, and black inset setpoint boxes.
"""

BACKGROUND = "#0b0d10"
PANEL = "#0e1c3c"
PANEL_BORDER = "#3f6faf"
ACCENT = "#5c9fff"
TEXT = "#e8ecf2"
MUTED = "#9db4d8"

YELLOW = "#ffd400"  # voltage
CYAN = "#00cfff"  # current
GREEN = "#00e676"  # power / CV / running
ORANGE = "#ff9100"  # CC
RED = "#e53935"  # protection alarms

STYLESHEET = f"""
QMainWindow, QWidget {{
    background: {BACKGROUND};
    color: {TEXT};
}}
QLabel {{
    background: transparent;
}}
QTabWidget::pane {{
    border: 1px solid {PANEL_BORDER};
    border-radius: 4px;
    background: {PANEL};
}}
QTabWidget::pane > QWidget {{
    background: {PANEL};
}}
QTabBar::tab {{
    background: #131a2a;
    color: {MUTED};
    border: 1px solid {PANEL_BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 14px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {PANEL};
    color: {TEXT};
    border-top: 2px solid {ACCENT};
}}
QDoubleSpinBox, QSpinBox, QComboBox {{
    background: black;
    color: white;
    border: 1px solid {ACCENT};
    border-radius: 3px;
    padding: 3px 6px;
    font-family: monospace;
    font-weight: bold;
    selection-background-color: {PANEL_BORDER};
}}
QComboBox QAbstractItemView {{
    background: {PANEL};
    color: {TEXT};
    border: 1px solid {PANEL_BORDER};
}}
QPushButton {{
    background: #131a2a;
    color: {TEXT};
    border: 1px solid {PANEL_BORDER};
    border-radius: 4px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    background: #1d2c4f;
}}
QPushButton:pressed {{
    background: {PANEL_BORDER};
}}
QPushButton:disabled {{
    color: #5a6a85;
    border-color: #2a3a55;
}}
QCheckBox {{
    background: transparent;
}}
QStatusBar {{
    background: #131a2a;
    color: {MUTED};
}}
"""
