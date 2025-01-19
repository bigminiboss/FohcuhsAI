from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon

class DoomscrollingPopup(QDialog): 
    def __init__(self, site, parent=None):
        super().__init__(parent)
        
        # Ensure the dialog stays open and visible
        self.setWindowFlags( 
            Qt.WindowType.Window | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Prevent automatic closing
        self.setModal(False)
        
        # Disable the close button in the title bar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        
        # Window configuration
        self.setWindowTitle("Doomscrolling Alert")
        
        # Prevent garbage collection
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        # Layout
        layout = QVBoxLayout()
        
        # Message
        message = QLabel(f"You've been on {site} for quite a while and we've detected signs of doomscrolling.\nConsider taking a break!")
        message.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #AAF0D1;
                margin: 10px;
            }
        """)
        layout.addWidget(message)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
        
        # Resize and center the popup
        self.resize(300, 150)
        self.center_on_screen()
        
    def center_on_screen(self):
        """Centers the popup on the screen"""
        frame_geometry = self.frameGeometry()
        screen = self.screen()
        center_point = screen.availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    def closeEvent(self, event):
        """Override close event to prevent automatic deletion"""
        event.ignore()
        self.hide()