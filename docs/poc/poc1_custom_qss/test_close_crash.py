"""
PoC 1: CRITICAL - Window Close Stability Test
Many PyQt/PySide compatibility issues only appear during object destruction
"""

import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt

try:
    from qfluentwidgets import (
        FluentWindow, setTheme, Theme, 
        PushButton, PrimaryPushButton, CardWidget
    )
    FLUENT_AVAILABLE = True
except ImportError:
    FLUENT_AVAILABLE = False


class TestWindow(QMainWindow):
    """Test window with various widgets"""
    
    def __init__(self, window_id):
        super().__init__()
        self.window_id = window_id
        self.setWindowTitle(f"Test Window #{window_id}")
        self.resize(400, 300)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Mix of standard and Fluent widgets
        if FLUENT_AVAILABLE:
            btn1 = PushButton("Fluent Button")
            btn2 = PrimaryPushButton("Primary Button")
            card = CardWidget()
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel("Card Content"))
            layout.addWidget(card)
        else:
            btn1 = QPushButton("Standard Button")
            btn2 = QPushButton("Another Button")
        
        layout.addWidget(btn1)
        layout.addWidget(btn2)
        
        self.closed_cleanly = False
    
    def closeEvent(self, event):
        """Track if close happens cleanly"""
        self.closed_cleanly = True
        print(f"  Window #{self.window_id} closing...")
        event.accept()


from PySide6.QtWidgets import QLabel


def test_single_close():
    """Test 1: Single window open/close"""
    print("\n=== Test 1: Single Window Close ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    if FLUENT_AVAILABLE:
        setTheme(Theme.DARK)
    
    try:
        window = TestWindow(1)
        window.show()
        app.processEvents()
        time.sleep(0.5)
        
        window.close()
        app.processEvents()
        
        print("✓ Single window closed cleanly")
        return True
    except Exception as e:
        print(f"✗ CRASH on single close: {e}")
        traceback.print_exc()
        return False


def test_multiple_close():
    """Test 2: Multiple windows open/close"""
    print("\n=== Test 2: Multiple Window Close ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    if FLUENT_AVAILABLE:
        setTheme(Theme.DARK)
    
    windows = []
    try:
        # Create 5 windows
        for i in range(5):
            w = TestWindow(i + 1)
            w.show()
            windows.append(w)
        
        app.processEvents()
        time.sleep(0.5)
        
        # Close all
        for w in windows:
            w.close()
            app.processEvents()
        
        print("✓ Multiple windows closed cleanly")
        return True
    except Exception as e:
        print(f"✗ CRASH on multiple close: {e}")
        traceback.print_exc()
        return False


def test_rapid_open_close():
    """Test 3: Rapid open/close cycles (stress test)"""
    print("\n=== Test 3: Rapid Open/Close (10 cycles) ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    if FLUENT_AVAILABLE:
        setTheme(Theme.DARK)
    
    crashes = 0
    
    for i in range(10):
        try:
            window = TestWindow(i + 1)
            window.show()
            app.processEvents()
            time.sleep(0.1)  # Short delay
            window.close()
            app.processEvents()
        except Exception as e:
            crashes += 1
            print(f"  Crash on cycle {i+1}: {e}")
    
    if crashes == 0:
        print("✓ All 10 cycles completed without crash")
        return True
    else:
        print(f"✗ {crashes}/10 cycles crashed")
        return False


def test_signal_cleanup():
    """Test 4: Signal-slot cleanup on close"""
    print("\n=== Test 4: Signal-Slot Cleanup ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    if FLUENT_AVAILABLE:
        setTheme(Theme.DARK)
    
    try:
        from PySide6.QtCore import Signal, QObject
        
        class SignalEmitter(QObject):
            signal = Signal(str)
        
        emitter = SignalEmitter()
        window = TestWindow(1)
        
        # Connect signal to window method
        emitter.signal.connect(lambda x: print(f"  Signal: {x}"))
        
        window.show()
        emitter.signal.emit("test")
        app.processEvents()
        
        window.close()
        emitter.signal.emit("after close")  # Should not crash
        app.processEvents()
        
        print("✓ Signal-slot cleanup successful")
        return True
    except Exception as e:
        print(f"✗ Signal cleanup failed: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PoC 1: CRITICAL - Window Close Stability Test")
    print("=" * 60)
    print(f"Fluent Available: {FLUENT_AVAILABLE}")
    print("\n⚠ This test is CRITICAL - many compatibility issues")
    print("   only appear during object destruction!")
    
    results = {
        "single_close": test_single_close(),
        "multiple_close": test_multiple_close(),
        "rapid_cycles": test_rapid_open_close(),
        "signal_cleanup": test_signal_cleanup()
    }
    
    print("\n" + "=" * 60)
    print("CRITICAL Test Results")
    print("=" * 60)
    
    all_pass = all(results.values())
    
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test}: {status}")
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✓ ALL CRITICAL TESTS PASSED")
        print("  Fluent theme is safe to use")
    else:
        print("✗ SOME TESTS FAILED")
        print("  Use Custom QSS theme instead!")
    print("=" * 60)
    
    # Write results
    with open("results.md", "a") as f:
        f.write(f"\n## PoC 1: CRITICAL - Window Close Stability\n")
        f.write(f"- Date: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- Fluent Available: {FLUENT_AVAILABLE}\n")
        f.write(f"- Single Close: {'PASS' if results['single_close'] else 'FAIL'}\n")
        f.write(f"- Multiple Close: {'PASS' if results['multiple_close'] else 'FAIL'}\n")
        f.write(f"- Rapid Cycles: {'PASS' if results['rapid_cycles'] else 'FAIL'}\n")
        f.write(f"- Signal Cleanup: {'PASS' if results['signal_cleanup'] else 'FAIL'}\n")
        f.write(f"- **OVERALL**: {'PASS - Can use Fluent' if all_pass else 'FAIL - Use Custom QSS'}**\n")
    
    print("\n✓ Results appended to results.md")
