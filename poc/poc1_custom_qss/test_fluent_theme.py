"""
PoC 1: Basic Fluent Theme Integration Test
Tests if PyQt-Fluent-Widgets applies theme without errors
"""

import sys
import time
from pathlib import Path

# Add src to path (copy code, don't modify src/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

# Test both theme options
try:
    # Check for PyQt5/PySide6 conflict first
    import PyQt5
    CONFLICT_DETECTED = True
    print("⚠⚠⚠ CRITICAL: PyQt5 detected alongside PySide6")
    print("   This causes class conflicts and crashes!")
    print("   Fix: pip uninstall PyQt5 PyQt5-Qt5")
    FLUENT_AVAILABLE = False
except ImportError:
    CONFLICT_DETECTED = False
    try:
        from qfluentwidgets import FluentWindow, setTheme, Theme, PushButton
        FLUENT_AVAILABLE = True
        print("✓ PyQt-Fluent-Widgets imported successfully")
    except ImportError as e:
        FLUENT_AVAILABLE = False
        print(f"⚠ PyQt-Fluent-Widgets not available: {e}")
        print("  Will test with standard QSS instead")


class BasicThemeTest(QWidget):
    """Test basic widget theming"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PoC 1: Basic Theme Test")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Test button with both libraries
        if FLUENT_AVAILABLE:
            btn = PushButton("Fluent Button")
            btn.setStyleSheet("background-color: #6C5DD3;")
        else:
            btn = QPushButton("Standard Button")
        
        layout.addWidget(btn)
        
        # Status label
        from PySide6.QtWidgets import QLabel
        status = QLabel(f"Theme: {'Fluent' if FLUENT_AVAILABLE else 'Standard QSS'}")
        layout.addWidget(status)


def test_basic_theme():
    """Test 1: Can we apply theme without errors?"""
    print("\n=== Test 1: Basic Theme Application ===")
    
    # Check for conflict
    if CONFLICT_DETECTED:
        print("✗ SKIPPED: PyQt5/PySide6 conflict detected")
        print("   Uninstall PyQt5: pip uninstall PyQt5 PyQt5-Qt5")
        return False
    
    # Create app (check if already exists)
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    if FLUENT_AVAILABLE:
        try:
            setTheme(Theme.DARK)
            print("✓ Fluent theme set successfully")
        except Exception as e:
            print(f"✗ Failed to set Fluent theme: {e}")
            return False
    
    window = BasicThemeTest()
    window.show()
    
    # Wait a moment
    app.processEvents()
    time.sleep(0.5)
    
    print("✓ Window rendered without errors")
    
    # Don't exec, just test creation
    window.close()
    return True


def test_startup_time():
    """Test 2: Measure startup time impact"""
    print("\n=== Test 2: Startup Time ===")
    
    start = time.time()
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    if FLUENT_AVAILABLE:
        setTheme(Theme.DARK)
    
    window = BasicThemeTest()
    window.show()
    app.processEvents()
    
    elapsed = time.time() - start
    print(f"Startup time: {elapsed:.3f}s")
    
    if elapsed > 2.0:
        print("⚠ Slow startup detected (>2s)")
    else:
        print("✓ Acceptable startup time")
    
    window.close()
    return elapsed


def test_memory_usage():
    """Test 3: Memory footprint"""
    print("\n=== Test 3: Memory Usage ===")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    if FLUENT_AVAILABLE:
        setTheme(Theme.DARK)
    
    windows = []
    for i in range(5):  # Create 5 windows
        w = BasicThemeTest()
        w.show()
        windows.append(w)
    
    app.processEvents()
    
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    increase = mem_after - mem_before
    
    print(f"Memory increase: {increase:.1f} MB")
    
    if increase > 100:
        print("⚠ High memory usage (>100MB)")
    else:
        print("✓ Acceptable memory usage")
    
    for w in windows:
        w.close()
    
    return increase


if __name__ == "__main__":
    print("=" * 60)
    print("PoC 1: PyQt-Fluent-Widgets - Basic Theme Test")
    print("=" * 60)
    
    results = {
        "basic_theme": test_basic_theme(),
        "startup_time": test_startup_time(),
        "memory_mb": test_memory_usage()
    }
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    for test, result in results.items():
        print(f"  {test}: {result}")
    
    # Write to results.md
    with open("results.md", "a") as f:
        f.write(f"\n## PoC 1: Basic Theme Test\n")
        f.write(f"- Date: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- PyQt5/PySide6 Conflict: {'DETECTED' if CONFLICT_DETECTED else 'None'}\n")
        f.write(f"- Fluent Available: {FLUENT_AVAILABLE}\n")
        f.write(f"- Basic Theme: {'PASS' if results['basic_theme'] else 'FAIL'}\n")
        f.write(f"- Startup Time: {results['startup_time']:.3f}s\n")
        f.write(f"- Memory Increase: {results['memory_mb']:.1f}MB\n")
        if CONFLICT_DETECTED:
            f.write(f"- **CRITICAL**: PyQt5 conflict must be resolved!\n")
    
    print("\n✓ Results appended to results.md")
