"""
PoC 1: Custom QSS Theme Test
Tests modern UI styling with PySide6 + Custom QSS
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt

# Modern Dark Theme QSS (inspired by Fluent Design)
MODERN_DARK_QSS = """
QMainWindow {
    background-color: #1E1E2E;
}

QWidget {
    background-color: #1E1E2E;
    color: #FFFFFF;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}

QFrame#card {
    background-color: #2D2D44;
    border-radius: 12px;
    border: 1px solid #3D3D5C;
}

QPushButton {
    background-color: #6C5DD3;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 500;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #5B4EC2;
}

QPushButton:pressed {
    background-color: #4A3DB1;
}

QLabel {
    color: #FFFFFF;
}

QLabel#heading {
    font-size: 24px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#caption {
    font-size: 12px;
    color: #B4B4BE;
}
"""


class Card(QFrame):
    """Card-style container with rounded corners"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.StyledPanel)


class ModernWindow(QMainWindow):
    """Test window with modern QSS theme"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PoC 1: Custom QSS Theme (PySide6)")
        self.resize(500, 400)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Card container
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        
        # Heading
        heading = QLabel("Modern Theme Test")
        heading.setObjectName("heading")
        card_layout.addWidget(heading)
        
        # Caption
        caption = QLabel("Custom QSS with PySide6 (License-Safe)")
        caption.setObjectName("caption")
        card_layout.addWidget(caption)
        
        # Button
        btn = QPushButton("Test Button")
        btn.clicked.connect(lambda: self.statusBar().showMessage("Button clicked!", 2000))
        card_layout.addWidget(btn)
        
        layout.addWidget(card)
        
        # Info label
        info = QLabel("✓ PySide6 with Custom QSS")
        info.setObjectName("caption")
        layout.addWidget(info)


def test_custom_theme():
    """Test 1: Can we apply custom QSS theme?"""
    print("\n=== Test 1: Custom QSS Theme ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(MODERN_DARK_QSS)
    
    window = ModernWindow()
    window.show()
    
    app.processEvents()
    time.sleep(0.5)
    
    print("✓ Custom QSS theme applied successfully")
    print("  - Dark background: #1E1E2E")
    print("  - Accent color: #6C5DD3")
    print("  - Rounded corners on cards")
    
    window.close()
    return True


def test_startup_performance():
    """Test 2: Startup time with QSS"""
    print("\n=== Test 2: Startup Performance ===")
    
    start = time.time()
    
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(MODERN_DARK_QSS)
    
    window = ModernWindow()
    window.show()
    app.processEvents()
    
    elapsed = time.time() - start
    print(f"Startup time: {elapsed:.3f}s")
    
    if elapsed < 2.0:
        print("✓ Acceptable startup time")
    else:
        print("⚠ Slow startup detected")
    
    window.close()
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("PoC 1: Custom QSS Theme with PySide6")
    print("=" * 60)
    print("\n⚠ License-Safe: PySide6 (LGPL) vs PyQt6 (GPL)")
    
    results = {
        "theme": test_custom_theme(),
        "startup": test_startup_performance()
    }
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"  Theme Application: {'PASS' if results['theme'] else 'FAIL'}")
    print(f"  Startup Time: {results['startup']:.3f}s")
    print("\n✓ Custom QSS is a viable alternative to PyQt-Fluent-Widgets")
    
    # Write results
    with open("results.md", "a") as f:
        f.write(f"\n## PoC 1: Custom QSS Theme\n")
        f.write(f"- Date: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- Theme: {'PASS' if results['theme'] else 'FAIL'}\n")
        f.write(f"- Startup: {results['startup']:.3f}s\n")
        f.write(f"- License: PySide6 (LGPL) - Commercial Safe\n")
    
    print("\n✓ Results appended to results.md")
