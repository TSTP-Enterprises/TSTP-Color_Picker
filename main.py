import sys
import os  # Added for resource_path
import sqlite3
import logging
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (
    QApplication,
    QColorDialog,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QMessageBox,
    QLabel,
    QPushButton,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QScrollArea,
)
from PyQt5.QtGui import QIcon, QColor, QCursor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from pynput import keyboard


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# Initialize logging
logging.basicConfig(
    filename="color_picker.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ColorLabel(QWidget):
    """A widget to display a saved color with its code and a copy button."""

    def __init__(self, red, green, blue, parent=None):
        super().__init__(parent)
        self.red = red
        self.green = green
        self.blue = blue
        self.initUI()

    def initUI(self):
        try:
            layout = QVBoxLayout()
            layout.setSpacing(1)
            layout.setContentsMargins(2, 2, 2, 2)
            self.setLayout(layout)

            # Color display
            self.color_display = QLabel()
            self.color_display.setFixedSize(40, 40)
            self.color_display.setStyleSheet(
                f"background-color: rgb({self.red}, {self.green}, {self.blue}); "
                "border: 1px solid #444; border-radius: 3px;"
            )
            layout.addWidget(self.color_display, alignment=Qt.AlignCenter)

            # Color code label
            self.color_code = QLabel(f"#{self.red:02X}{self.green:02X}{self.blue:02X}")
            self.color_code.setAlignment(Qt.AlignCenter)
            self.color_code.setStyleSheet("color: #f0f0f0; font-size: 10px;")
            layout.addWidget(self.color_code)

            # Copy button
            self.copy_button = QPushButton("Copy")
            self.copy_button.setFixedSize(50, 22)
            self.copy_button.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    border: 1px solid #666;
                    border-radius: 3px;
                    color: white;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
            self.copy_button.clicked.connect(self.copyColorCode)
            layout.addWidget(self.copy_button, alignment=Qt.AlignCenter)

            # Color preview on hover
            self.preview_label = QLabel(self)
            self.preview_label.setFixedSize(50, 20)
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 200);
                    color: white;
                    border-radius: 3px;
                    font-size: 8px;
                }
            """)
            self.preview_label.setAlignment(Qt.AlignCenter)
            self.preview_label.setText(self.color_code.text())
            self.preview_label.move(self.color_display.x(), self.color_display.y() - 25)
            self.preview_label.hide()

        except Exception as e:
            logging.error("Error initializing ColorLabel: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to initialize a color label.")

    def copyColorCode(self):
        """Copy the color code to the clipboard."""
        try:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(self.color_code.text())
            logging.info(f"Copied color code {self.color_code.text()} to clipboard.")
        except Exception as e:
            logging.error("Error copying color code to clipboard: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to copy color code.")

    def enterEvent(self, event):
        """Show the color preview label on hover."""
        self.preview_label.show()

    def leaveEvent(self, event):
        """Hide the color preview label when not hovering."""
        self.preview_label.hide()


class HotkeyListener(QObject):
    """A class to listen for global hotkeys using pynput."""
    color_picked = pyqtSignal(int, int, int)

    def __init__(self):
        super().__init__()
        self.is_alt_pressed = False
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

    def on_press(self, key):
        try:
            if key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.is_alt_pressed = True
            elif self.is_alt_pressed and key == keyboard.KeyCode.from_char('1'):
                # Capture color at cursor position
                pos = QCursor.pos()
                x, y = pos.x(), pos.y()
                screen = QtWidgets.QApplication.screenAt(pos)
                if not screen:
                    screen = QtWidgets.QApplication.primaryScreen()
                if screen is None:
                    return
                relative_x = x - screen.geometry().x()
                relative_y = y - screen.geometry().y()
                if relative_x < 0 or relative_y < 0 or relative_x >= screen.size().width() or relative_y >= screen.size().height():
                    return
                pixmap = screen.grabWindow(0)
                if 0 <= relative_x < pixmap.width() and 0 <= relative_y < pixmap.height():
                    color = pixmap.toImage().pixelColor(relative_x, relative_y)
                    self.color_picked.emit(color.red(), color.green(), color.blue())
        except Exception as e:
            logging.error("Error in hotkey listener on_press: %s", str(e))

    def on_release(self, key):
        try:
            if key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.is_alt_pressed = False
        except Exception as e:
            logging.error("Error in hotkey listener on_release: %s", str(e))

    def stop(self):
        """Stop the keyboard listener."""
        self.listener.stop()


class ColorPickerOverlay(QWidget):
    """An overlay widget to display color information under the cursor."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(1.0)  # Fully opaque for text visibility
        self.cursor_color_label = QLabel(self)
        self.cursor_color_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 5px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.cursor_color_label.setVisible(False)  # Initially hidden
        self.setMouseTracking(True)
        self.current_color = QColor(0, 0, 0)

        # Instruction Label under the color code
        self.instruction_label = QLabel("(ALT+1 to Pick / ESC to Cancel)", self)
        self.instruction_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);
                color: white;
                padding: 3px;
                border-radius: 3px;
                font-size: 10px;
            }
        """)
        self.instruction_label.adjustSize()
        self.instruction_label.move(20, 20)
        self.instruction_label.setVisible(False)  # Initially hidden

        # Timer to update color under cursor
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_color)

    def resizeEvent(self, event):
        """Ensure labels are repositioned if the overlay size changes."""
        super().resizeEvent(event)
        # Position instruction label
        self.instruction_label.move(20, 20)

    def start_overlay(self):
        """Start the overlay display."""
        self.timer.start(30)  # Update every 30ms
        self.instruction_label.setVisible(True)
        self.cursor_color_label.setVisible(True)
        self.activateWindow()
        self.raise_()
        logging.info("Overlay started.")

    def stop_overlay(self):
        """Stop the overlay display."""
        self.timer.stop()
        self.cursor_color_label.setVisible(False)
        self.instruction_label.setVisible(False)
        self.hide()
        logging.info("Overlay stopped.")

    def update_color(self):
        """Update the color under the cursor and display previews."""
        try:
            pos = QCursor.pos()
            x, y = pos.x(), pos.y()
            screen = QtWidgets.QApplication.screenAt(pos)
            if not screen:
                screen = QtWidgets.QApplication.primaryScreen()
            if screen is None:
                return

            # Adjust coordinates relative to the screen
            relative_x = x - screen.geometry().x()
            relative_y = y - screen.geometry().y()

            if relative_x < 0 or relative_y < 0 or \
               relative_x >= screen.size().width() or \
               relative_y >= screen.size().height():
                return

            # Capture the pixel color at the cursor position
            pixmap = screen.grabWindow(0)
            if 0 <= relative_x < pixmap.width() and 0 <= relative_y < pixmap.height():
                color = pixmap.toImage().pixelColor(relative_x, relative_y)
            else:
                color = QColor(0, 0, 0)

            self.current_color = color

            # Update the cursor color label
            self.cursor_color_label.setText(f"#{color.red():02X}{color.green():02X}{color.blue():02X}")
            self.cursor_color_label.adjustSize()

            # Determine label position relative to overlay
            overlay_x = self.geometry().x()
            overlay_y = self.geometry().y()
            local_x = x - overlay_x
            local_y = y - overlay_y

            # Position the color code label near the cursor
            label_width = self.cursor_color_label.width()
            label_height = self.cursor_color_label.height()

            # Prevent label from going off the right edge
            if local_x + 15 + label_width > self.width():
                new_x = local_x - label_width - 15
            else:
                new_x = local_x + 15

            # Prevent label from going off the bottom edge
            if local_y + 15 + label_height > self.height():
                new_y = local_y - label_height - 15
            else:
                new_y = local_y + 15

            self.cursor_color_label.move(new_x, new_y)
            self.cursor_color_label.setVisible(True)

            # Position the instruction label right below the color code
            instruction_x = new_x
            instruction_y = new_y + label_height + 5  # 5 pixels below the color code
            self.instruction_label.move(instruction_x, instruction_y)
            self.instruction_label.setVisible(True)

        except Exception as e:
            logging.error("Error updating color in overlay: %s", str(e))


class ColorPickerApp(QtWidgets.QMainWindow):
    """Main application window for the Color Picker."""

    def __init__(self):
        super().__init__()

        self.always_on_top = False  # Track 'Always stay on top' state
        self.max_columns = 6  # Number of columns in the grid
        self.current_count = 0  # Number of colors added
        self.last_color = QColor(0, 0, 0)
        self.initUI()
        self.createDatabase()
        self.loadSavedColors()
        self.initSystemTray()

        # Initialize overlay
        self.overlay = ColorPickerOverlay()

        # Initialize hotkey listener
        self.hotkey_thread = None
        self.hotkey_listener = None

    def initUI(self):
        """Initialize the main UI components."""
        try:
            # Set window title and icon using resource_path
            icon_path = resource_path('app_icon.ico')
            self.setWindowTitle('Color Picker')
            self.setWindowIcon(QIcon(icon_path))

            # Apply dark theme with 3D effects
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    border: 1px solid #444;
                    border-radius: 10px;
                    padding: 10px;
                }
                QLabel, QPushButton, QLineEdit {
                    color: #f0f0f0;
                }
                QPushButton {
                    background-color: #555;
                    border: 2px solid #666;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
                QPushButton:pressed {
                    background-color: #666;
                }
            """)

            # Main layout
            self.centralWidget = QtWidgets.QWidget(self)
            self.setCentralWidget(self.centralWidget)
            self.layout = QtWidgets.QVBoxLayout(self.centralWidget)
            self.layout.setSpacing(10)

            # Header
            header = QtWidgets.QLabel("TSTP Color Picker")
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("font-size: 18px; font-weight: bold;")
            self.layout.addWidget(header)

            # Buttons layout
            buttons_layout = QHBoxLayout()

            # Pick Color button
            self.colorButton = QPushButton('Pick Color', self)
            self.colorButton.clicked.connect(self.pickColor)
            buttons_layout.addWidget(self.colorButton)

            # Pick Color From Screen button
            self.screenColorButton = QPushButton('Pick Color From Screen', self)
            self.screenColorButton.setCheckable(True)
            self.screenColorButton.clicked.connect(self.togglePickFromScreen)
            buttons_layout.addWidget(self.screenColorButton)

            # Always Stay On Top Toggle
            self.topButton = QPushButton('Always Stay On Top', self)
            self.topButton.setCheckable(True)
            self.topButton.clicked.connect(self.toggleAlwaysOnTop)
            buttons_layout.addWidget(self.topButton)

            self.layout.addLayout(buttons_layout)

            # Grid layout for saved colors inside a scroll area
            self.scrollArea = QScrollArea()
            self.scrollArea.setWidgetResizable(True)
            self.gridWidget = QWidget()
            self.gridLayout = QGridLayout(self.gridWidget)
            self.gridLayout.setSpacing(3)  # Smaller spacing
            self.scrollArea.setWidget(self.gridWidget)
            self.layout.addWidget(self.scrollArea)

            # Set minimum size
            self.setMinimumSize(500, 400)

        except Exception as e:
            logging.error("Error initializing UI: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to initialize UI.")

    def createDatabase(self):
        """Create or connect to SQLite database."""
        try:
            self.conn = sqlite3.connect("colors.db")
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS colors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    red INTEGER NOT NULL,
                    green INTEGER NOT NULL,
                    blue INTEGER NOT NULL
                )
            """)
            self.conn.commit()
            logging.info("Database connected and ensured table exists.")
        except Exception as e:
            logging.error("Error creating database: %s", str(e))
            QMessageBox.critical(self, "Database Error", "Failed to create or connect to the database.")

    def initSystemTray(self):
        """Create system tray icon and menu."""
        try:
            tray_icon_path = resource_path("app_icon.ico")
            self.trayIcon = QSystemTrayIcon(QIcon(tray_icon_path), self)
            self.trayIcon.setToolTip("Color Picker App")

            # Create the menu for the system tray
            trayMenu = QMenu()

            pickFromScreenAction = QAction("Pick Color From Screen", self)
            pickFromScreenAction.setCheckable(True)
            pickFromScreenAction.triggered.connect(self.togglePickFromScreen)
            trayMenu.addAction(pickFromScreenAction)

            showAction = QAction("Show", self)
            showAction.triggered.connect(self.showWindow)
            trayMenu.addAction(showAction)

            toggleTopAction = QAction("Always Stay On Top", self)
            toggleTopAction.setCheckable(True)
            toggleTopAction.triggered.connect(self.toggleAlwaysOnTopTray)
            trayMenu.addAction(toggleTopAction)

            quitAction = QAction("Quit", self)
            quitAction.triggered.connect(QtWidgets.qApp.quit)
            trayMenu.addAction(quitAction)

            self.trayIcon.setContextMenu(trayMenu)
            self.trayIcon.activated.connect(self.onTrayIconActivated)
            self.trayIcon.show()
            logging.info("System tray initialized.")
        except Exception as e:
            logging.error("Error initializing system tray: %s", str(e))
            QMessageBox.critical(self, "Tray Error", "Failed to initialize system tray.")

    def onTrayIconActivated(self, reason):
        """Handle tray icon clicks."""
        if reason == QSystemTrayIcon.Trigger:
            self.showWindow()

    def showWindow(self):
        """Restore the window from the system tray."""
        self.showNormal()
        self.activateWindow()

    def toggleAlwaysOnTop(self):
        """Toggle 'Always stay on top' for the window."""
        try:
            if self.always_on_top:
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                self.always_on_top = False
                self.topButton.setChecked(False)
                # Reset button style to default
                self.topButton.setStyleSheet("""
                    QPushButton {
                        background-color: #555;
                        border: 2px solid #666;
                        border-radius: 5px;
                        padding: 5px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #666;
                    }
                """)
                # Update tray menu
                self.trayIcon.contextMenu().actions()[2].setChecked(False)  # ToggleTopAction
                logging.info("Disabled 'Always stay on top'.")
            else:
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
                self.always_on_top = True
                self.topButton.setChecked(True)
                # Change button style to green
                self.topButton.setStyleSheet("""
                    QPushButton {
                        background-color: green;
                        border: 2px solid #666;
                        border-radius: 5px;
                        padding: 5px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #44aa44;
                    }
                """)
                # Update tray menu
                self.trayIcon.contextMenu().actions()[2].setChecked(True)  # ToggleTopAction
                logging.info("Enabled 'Always stay on top'.")
            self.show()
        except Exception as e:
            logging.error("Error toggling 'Always stay on top': %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to toggle 'Always stay on top'.")

    def toggleAlwaysOnTopTray(self, checked):
        """Toggle 'Always stay on top' from system tray."""
        try:
            if checked:
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
                self.always_on_top = True
                self.topButton.setChecked(True)
                # Change button style to green
                self.topButton.setStyleSheet("""
                    QPushButton {
                        background-color: green;
                        border: 2px solid #666;
                        border-radius: 5px;
                        padding: 5px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #44aa44;
                    }
                """)
                logging.info("Enabled 'Always stay on top' from tray.")
            else:
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                self.always_on_top = False
                self.topButton.setChecked(False)
                # Reset button style to default
                self.topButton.setStyleSheet("""
                    QPushButton {
                        background-color: #555;
                        border: 2px solid #666;
                        border-radius: 5px;
                        padding: 5px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #666;
                    }
                """)
                logging.info("Disabled 'Always stay on top' from tray.")
            self.show()
        except Exception as e:
            logging.error("Error toggling 'Always stay on top' from tray: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to toggle 'Always stay on top' from tray.")

    def togglePickFromScreen(self):
        """Toggle the screen color picking mode."""
        try:
            if self.screenColorButton.isChecked():
                self.screenColorButton.setStyleSheet("""
                    QPushButton {
                        background-color: green;
                        border: 2px solid #666;
                        border-radius: 5px;
                        padding: 5px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #44aa44;
                    }
                """)
                # Update tray menu
                self.trayIcon.contextMenu().actions()[0].setChecked(True)  # PickFromScreenAction
                self.start_hotkey_listener()
                self.overlay.showFullScreen()  # Ensure overlay is shown on all monitors
                self.overlay.start_overlay()
                self.overlay.setGeometry(QApplication.desktop().screenGeometry())  # Set overlay to cover all screens
                logging.info("Pick Color From Screen enabled.")
            else:
                self.screenColorButton.setStyleSheet("""
                    QPushButton {
                        background-color: #555;
                        border: 2px solid #666;
                        border-radius: 5px;
                        padding: 5px;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #666;
                    }
                """)
                # Update tray menu
                self.trayIcon.contextMenu().actions()[0].setChecked(False)  # PickFromScreenAction
                self.stop_hotkey_listener()
                self.overlay.hide()  # Hide the overlay
                self.overlay.stop_overlay()
                logging.info("Pick Color From Screen disabled.")
        except Exception as e:
            logging.error("Error toggling Pick Color From Screen: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to toggle Pick Color From Screen.")

    def pickColor(self):
        """Open color picker dialog and save selected color."""
        try:
            color = QColorDialog.getColor()
            if color.isValid():
                # Check for duplicates
                existing_color = self.getColorFromDatabase(color.red(), color.green(), color.blue())
                if existing_color:
                    self.removeColor(existing_color[0], color.red(), color.green(), color.blue())
                self.saveColor(color.red(), color.green(), color.blue())
        except Exception as e:
            logging.error("Error picking color: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to pick color.")

    def saveColor(self, red, green, blue):
        """Save selected color to the database and display it in the grid."""
        try:
            # Update last color
            self.last_color = QColor(red, green, blue)

            # Check for duplicates
            existing_color = self.getColorFromDatabase(red, green, blue)
            if existing_color:
                self.removeColor(existing_color[0], red, green, blue)

            # Insert into database
            self.cursor.execute(
                "INSERT INTO colors (red, green, blue) VALUES (?, ?, ?)",
                (red, green, blue)
            )
            self.conn.commit()
            logging.info(f"Saved color RGB({red}, {green}, {blue}) to database.")

            # Refresh grid
            self.refreshGrid()
        except Exception as e:
            logging.error("Error saving color to database: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to save color.")

    def getColorFromDatabase(self, red, green, blue):
        """Check if the color already exists in the database."""
        try:
            self.cursor.execute(
                "SELECT id FROM colors WHERE red=? AND green=? AND blue=?",
                (red, green, blue)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logging.error("Error checking duplicate color in database: %s", str(e))
            return None

    def removeColor(self, color_id, red, green, blue):
        """Remove the color from the database and grid."""
        try:
            # Remove from database
            self.cursor.execute(
                "DELETE FROM colors WHERE id=?",
                (color_id,)
            )
            self.conn.commit()
            logging.info(f"Removed duplicate color RGB({red}, {green}, {blue}) from database.")

            # Refresh grid
            self.refreshGrid()
        except Exception as e:
            logging.error("Error removing duplicate color: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to remove duplicate color.")

    def loadSavedColors(self):
        """Load saved colors from the database and display in the grid."""
        try:
            self.cursor.execute("SELECT red, green, blue FROM colors")
            colors = self.cursor.fetchall()
            for color in colors:
                red, green, blue = color
                self.addColorToGrid(red, green, blue)
            logging.info("Loaded saved colors from database.")
        except Exception as e:
            logging.error("Error loading colors from database: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to load saved colors.")

    def addColorToGrid(self, red, green, blue):
        """Add a color square to the grid layout in a 6x grid."""
        try:
            color_label = ColorLabel(red, green, blue)
            row = self.current_count // self.max_columns
            col = self.current_count % self.max_columns
            self.gridLayout.addWidget(color_label, row, col)
            self.current_count += 1
            logging.info(f"Added color RGB({red}, {green}, {blue}) to grid at row {row}, column {col}.")
        except Exception as e:
            logging.error("Error adding color to grid: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to display color.")

    def refreshGrid(self):
        """Refresh the entire grid layout."""
        try:
            # Clear grid
            while self.gridLayout.count():
                item = self.gridLayout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)

            # Reload colors
            self.current_count = 0
            self.cursor.execute("SELECT red, green, blue FROM colors")
            colors = self.cursor.fetchall()
            for color in colors:
                red, green, blue = color
                self.addColorToGrid(red, green, blue)
        except Exception as e:
            logging.error("Error refreshing grid: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to refresh color grid.")

    def getAllColors(self):
        """Retrieve all colors from the database."""
        try:
            self.cursor.execute("SELECT red, green, blue FROM colors")
            return self.cursor.fetchall()
        except Exception as e:
            logging.error("Error retrieving all colors: %s", str(e))
            return []

    def closeEvent(self, event):
        """Handle application close event (save state, etc.)."""
        try:
            self.conn.close()
            logging.info("Database connection closed.")
        except Exception as e:
            logging.error("Error closing database: %s", str(e))
        # Ensure hotkey listener is stopped
        self.stop_hotkey_listener()
        event.accept()

    def start_hotkey_listener(self):
        """Start the global hotkey listener in a separate thread."""
        if self.hotkey_thread is None:
            self.hotkey_thread = QThread()
            self.hotkey_listener = HotkeyListener()
            self.hotkey_listener.moveToThread(self.hotkey_thread)
            self.hotkey_listener.color_picked.connect(self.saveColor)
            self.hotkey_thread.started.connect(lambda: None)  # No specific start action
            self.hotkey_thread.start()
            logging.info("Hotkey listener thread started.")

    def stop_hotkey_listener(self):
        """Stop the global hotkey listener."""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        if self.hotkey_thread:
            self.hotkey_thread.quit()
            self.hotkey_thread.wait()
            self.hotkey_thread = None
            logging.info("Hotkey listener thread stopped.")


def main():
    """Main function to run the application."""
    try:
        app = QtWidgets.QApplication(sys.argv)
        # Set application style for better visuals
        app.setStyle("Fusion")
        window = ColorPickerApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical("Application crashed: %s", str(e))
        QMessageBox.critical(None, "Critical Error", "The application has crashed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
