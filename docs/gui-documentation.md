# Modern GUI Documentation

## VoiceTranslate Pro - User Interface Design and Implementation

This document describes the modern graphical user interface of VoiceTranslate Pro, including design principles, components, themes, and implementation details.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [UI Components](#ui-components)
3. [Themes and Styling](#themes-and-styling)
4. [Responsive Design](#responsive-design)
5. [Accessibility](#accessibility)
6. [Animations and Transitions](#animations-and-transitions)
7. [Implementation Details](#implementation-details)
8. [Customization](#customization)

---

## Design Philosophy

### Core Principles

1. **Clarity**: Interface should be immediately understandable
2. **Efficiency**: Minimize clicks and cognitive load
3. **Beauty**: Modern, polished appearance
4. **Consistency**: Uniform patterns throughout
5. **Accessibility**: Usable by everyone

### Design Language

VoiceTranslate Pro uses a **modern, minimalist design language** inspired by:

- Material Design 3 (Google)
- Fluent Design (Microsoft)
- Human Interface Guidelines (Apple)

### Visual Hierarchy

```
Primary Actions (Start/Stop)
    ↓
Secondary Actions (Settings, Save)
    ↓
Information Display (Translation, Transcription)
    ↓
Status and Feedback
```

---

## UI Components

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  [Icon] VoiceTranslate Pro                    [_] [□] [X]      │  ← Title Bar
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │  ← Control Bar
│  │ 🌐 English ▼ │  │ 🌐 中文 ▼    │  │ [⚙] [📹] [💾] [?]   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │  ← Transcription
│  │  🎤 Listening...                                        │   │
│  │  "Hello, how are you today?"                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │  ← Translation
│  │  🌐 Translation                                         │   │
│  │  "你好，你今天怎么样？"                                   │   │
│  │  [Confidence: 98%]                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │  ← Audio Visualizer
│  │     ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │  ← Action Bar
│  │        [  ⏹ Stop Translation  ]                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Status: Active | Latency: 245ms | Model: Whisper Medium      │  ← Status Bar
└─────────────────────────────────────────────────────────────────┘
```

### Component Library

#### 1. Language Selector

```python
class LanguageComboBox(QComboBox):
    """Modern language selector with search and flags."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background: white;
                font-size: 14px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(:/icons/dropdown.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                selection-background-color: #E3F2FD;
            }
        """)
        self.setMaxVisibleItems(10)
        self.setEditable(True)
```

**Features:**
- Searchable dropdown
- Country flag icons
- Recently used languages
- Favorites section

#### 2. Translation Display

```python
class TranslationDisplay(QTextEdit):
    """Rich translation display with confidence indicators."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                border: 2px solid #E0E0E0;
                border-radius: 12px;
                padding: 16px;
                background: #FAFAFA;
                font-size: 18px;
                line-height: 1.6;
            }
        """)
    
    def set_translation(self, text: str, confidence: float):
        """Display translation with confidence indicator."""
        color = self._confidence_color(confidence)
        html = f"""
        <div style="font-size: 24px; margin-bottom: 12px;">
            {text}
        </div>
        <div style="color: {color}; font-size: 12px;">
            Confidence: {confidence:.0%}
        </div>
        """
        self.setHtml(html)
    
    def _confidence_color(self, confidence: float) -> str:
        if confidence >= 0.9:
            return "#4CAF50"  # Green
        elif confidence >= 0.7:
            return "#FF9800"  # Orange
        else:
            return "#F44336"  # Red
```

#### 3. Audio Visualizer

```python
class AudioVisualizer(QWidget):
    """Real-time audio level visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.levels = [0.0] * 30
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)  # 20 FPS
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor("#F5F5F5"))
        
        # Draw bars
        bar_width = self.width() / len(self.levels)
        for i, level in enumerate(self.levels):
            x = i * bar_width
            height = level * self.height()
            y = self.height() - height
            
            # Gradient color based on level
            if level < 0.5:
                color = QColor("#4CAF50")
            elif level < 0.8:
                color = QColor("#FF9800")
            else:
                color = QColor("#F44336")
            
            painter.fillRect(
                int(x) + 1, int(y),
                int(bar_width) - 2, int(height),
                color
            )
    
    def update_level(self, level: float):
        """Update audio level."""
        self.levels.pop(0)
        self.levels.append(min(level, 1.0))
        self.update()
```

#### 4. Status Bar

```python
class StatusBar(QStatusBar):
    """Modern status bar with animated indicators."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QStatusBar {
                background: #FAFAFA;
                border-top: 1px solid #E0E0E0;
                padding: 8px 16px;
            }
        """)
        
        # Status indicator
        self.status_label = QLabel("Ready")
        self.addWidget(self.status_label)
        
        # Latency indicator
        self.latency_label = QLabel("Latency: --")
        self.addPermanentWidget(self.latency_label)
        
        # Model indicator
        self.model_label = QLabel("Model: --")
        self.addPermanentWidget(self.model_label)
    
    def set_status(self, status: str, animated: bool = False):
        """Update status with optional animation."""
        if animated:
            # Add pulsing dot animation
            self.status_label.setText(f"● {status}")
        else:
            self.status_label.setText(status)
```

#### 5. Primary Action Button

```python
class ActionButton(QPushButton):
    """Large, prominent action button."""
    
    def __init__(self, text: str, icon: str, parent=None):
        super().__init__(text, parent)
        self.setIcon(QIcon(icon))
        self.setIconSize(QSize(24, 24))
        self.setMinimumHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                border: none;
                border-radius: 24px;
                padding: 12px 32px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #42A5F5, stop:1 #1E88E5);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1976D2, stop:1 #1565C0);
            }
            QPushButton:disabled {
                background: #BDBDBD;
            }
        """)
```

---

## Themes and Styling

### Theme System

```python
class ThemeManager:
    """Manage application themes."""
    
    THEMES = {
        "light": LightTheme(),
        "dark": DarkTheme(),
        "auto": AutoTheme(),
    }
    
    def __init__(self):
        self.current_theme = "light"
    
    def apply_theme(self, theme_name: str):
        """Apply theme to application."""
        theme = self.THEMES.get(theme_name, self.THEMES["light"])
        QApplication.instance().setStyleSheet(theme.stylesheet)
        self.current_theme = theme_name
```

### Light Theme

```python
class LightTheme:
    """Light color theme."""
    
    colors = {
        "primary": "#2196F3",
        "primary_dark": "#1976D2",
        "secondary": "#FF4081",
        "background": "#FFFFFF",
        "surface": "#FAFAFA",
        "error": "#F44336",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "divider": "#E0E0E0",
    }
    
    stylesheet = """
        /* Main Window */
        QMainWindow {
            background-color: #FFFFFF;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 14px;
        }
        
        QPushButton:hover {
            background-color: #1976D2;
        }
        
        /* Input Fields */
        QLineEdit, QTextEdit {
            background-color: #FAFAFA;
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border-color: #2196F3;
        }
        
        /* Combo Boxes */
        QComboBox {
            background-color: white;
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            padding: 8px;
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            background: #F5F5F5;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: #BDBDBD;
            border-radius: 6px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: #9E9E9E;
        }
    """
```

### Dark Theme

```python
class DarkTheme:
    """Dark color theme."""
    
    colors = {
        "primary": "#90CAF9",
        "primary_dark": "#64B5F6",
        "secondary": "#F48FB1",
        "background": "#121212",
        "surface": "#1E1E1E",
        "error": "#EF5350",
        "success": "#66BB6A",
        "warning": "#FFA726",
        "text_primary": "#FFFFFF",
        "text_secondary": "#B0B0B0",
        "divider": "#424242",
    }
    
    stylesheet = """
        QMainWindow {
            background-color: #121212;
        }
        
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
        }
        
        QPushButton:hover {
            background-color: #42A5F5;
        }
        
        QLineEdit, QTextEdit {
            background-color: #1E1E1E;
            border: 2px solid #424242;
            color: #FFFFFF;
            border-radius: 8px;
            padding: 10px;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border-color: #90CAF9;
        }
        
        QLabel {
            color: #FFFFFF;
        }
        
        QComboBox {
            background-color: #1E1E1E;
            border: 2px solid #424242;
            color: #FFFFFF;
            border-radius: 8px;
            padding: 8px;
        }
    """
```

### Theme Switching

```python
# In settings dialog
def on_theme_changed(self, theme_name: str):
    """Handle theme change."""
    theme_manager.apply_theme(theme_name)
    
    # Save preference
    config.set("gui.theme", theme_name)
    
    # Show restart notification if needed
    if theme_name == "auto":
        self.show_info("Theme will follow system settings")
```

---

## Responsive Design

### Window Sizing

```python
class MainWindow(QMainWindow):
    """Main application window with responsive layout."""
    
    MIN_WIDTH = 800
    MIN_HEIGHT = 600
    DEFAULT_WIDTH = 1000
    DEFAULT_HEIGHT = 700
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        
        # Central widget with responsive layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup responsive UI components."""
        # Control bar (horizontal, wraps on small screens)
        self.control_bar = self._create_control_bar()
        self.main_layout.addWidget(self.control_bar)
        
        # Translation displays (expand to fill space)
        self.transcription_display = TranslationDisplay()
        self.transcription_display.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.main_layout.addWidget(self.transcription_display)
        
        self.translation_display = TranslationDisplay()
        self.translation_display.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.main_layout.addWidget(self.translation_display)
        
        # Audio visualizer (fixed height)
        self.visualizer = AudioVisualizer()
        self.visualizer.setFixedHeight(80)
        self.main_layout.addWidget(self.visualizer)
        
        # Action button (fixed height, centered)
        self.action_button = ActionButton("Start Translation", ":/icons/mic.png")
        self.action_button.setMaximumWidth(300)
        self.main_layout.addWidget(self.action_button, alignment=Qt.AlignCenter)
```

### Layout Breakpoints

```python
class ResponsiveLayout:
    """Handle responsive layout changes."""
    
    BREAKPOINTS = {
        "compact": 600,
        "medium": 900,
        "large": 1200,
    }
    
    def __init__(self, window: QMainWindow):
        self.window = window
        self.current_layout = "medium"
    
    def on_resize(self, event):
        """Handle window resize."""
        width = self.window.width()
        
        if width < self.BREAKPOINTS["compact"]:
            self._apply_compact_layout()
        elif width < self.BREAKPOINTS["medium"]:
            self._apply_medium_layout()
        else:
            self._apply_large_layout()
    
    def _apply_compact_layout(self):
        """Stack all elements vertically."""
        if self.current_layout != "compact":
            # Reorganize for small screens
            self.current_layout = "compact"
    
    def _apply_medium_layout(self):
        """Side-by-side language selectors."""
        if self.current_layout != "medium":
            self.current_layout = "medium"
    
    def _apply_large_layout(self):
        """Full layout with all features visible."""
        if self.current_layout != "large":
            self.current_layout = "large"
```

---

## Accessibility

### WCAG 2.1 Compliance

VoiceTranslate Pro aims for WCAG 2.1 Level AA compliance:

| Guideline | Implementation |
|-----------|----------------|
| 1.4.3 Contrast | Minimum 4.5:1 for normal text |
| 1.4.4 Resize | Text resizable up to 200% |
| 2.1.1 Keyboard | All functions keyboard accessible |
| 2.4.3 Focus Order | Logical tab order |
| 4.1.2 Name, Role, Value | Proper ARIA labels |

### Keyboard Navigation

```python
class AccessibleMainWindow(QMainWindow):
    """Main window with accessibility features."""
    
    def __init__(self):
        super().__init__()
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Start/Stop: Space
        self.shortcut_start = QShortcut(
            QKeySequence("Space"), self
        )
        self.shortcut_start.activated.connect(self.toggle_translation)
        
        # Settings: Ctrl+,
        self.shortcut_settings = QShortcut(
            QKeySequence("Ctrl+,"), self
        )
        self.shortcut_settings.activated.connect(self.open_settings)
        
        # Swap languages: Ctrl+L
        self.shortcut_swap = QShortcut(
            QKeySequence("Ctrl+L"), self
        )
        self.shortcut_swap.activated.connect(self.swap_languages)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Tab:
            # Custom tab navigation
            self.focusNextChild()
        elif event.key() == Qt.Key_Escape:
            # Stop current operation
            self.stop_translation()
        else:
            super().keyPressEvent(event)
```

### Screen Reader Support

```python
class AccessibleWidget(QWidget):
    """Widget with screen reader support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName("Translation Display")
        self.setAccessibleDescription(
            "Shows the translated text in the target language"
        )
    
    def update_translation(self, text: str):
        """Update translation and notify screen reader."""
        self.setText(text)
        
        # Emit accessible notification
        QAccessible.updateAccessibility(
            QAccessibleEvent(self, QAccessible.NameChanged)
        )
```

### High Contrast Mode

```python
class HighContrastTheme:
    """High contrast theme for accessibility."""
    
    colors = {
        "background": "#000000",
        "text": "#FFFFFF",
        "primary": "#FFFF00",
        "secondary": "#00FFFF",
        "border": "#FFFFFF",
    }
    
    stylesheet = """
        QMainWindow {
            background-color: #000000;
        }
        
        QLabel {
            color: #FFFFFF;
            font-weight: bold;
        }
        
        QPushButton {
            background-color: #000000;
            color: #FFFFFF;
            border: 2px solid #FFFFFF;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #FFFF00;
            color: #000000;
        }
    """
```

---

## Animations and Transitions

### Smooth Transitions

```python
class AnimatedWidget(QWidget):
    """Widget with smooth animations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_animations()
    
    def _setup_animations(self):
        """Setup property animations."""
        # Fade in animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Slide animation
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def show_animated(self):
        """Show with fade animation."""
        self.fade_animation.start()
        self.show()
```

### Microphone Pulse Animation

```python
class PulsingButton(QPushButton):
    """Button with pulsing animation when active."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._setup_pulse_animation()
    
    def _setup_pulse_animation(self):
        """Setup pulsing glow effect."""
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setColor(QColor("#2196F3"))
        self.glow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.glow_effect)
        
        self.pulse_animation = QPropertyAnimation(
            self.glow_effect, b"blurRadius"
        )
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(10)
        self.pulse_animation.setEndValue(30)
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutSine)
        self.pulse_animation.setLoopCount(-1)  # Infinite
        self.pulse_animation.setDirection(QPropertyAnimation.Forward)
    
    def start_pulsing(self):
        """Start pulse animation."""
        self.pulse_animation.start()
    
    def stop_pulsing(self):
        """Stop pulse animation."""
        self.pulse_animation.stop()
        self.glow_effect.setBlurRadius(0)
```

---

## Implementation Details

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| GUI Framework | PyQt6 / PySide6 | 6.4+ |
| Styling | QSS (Qt Style Sheets) | - |
| Icons | Material Design Icons | 7.0+ |
| Fonts | Roboto, Noto Sans | Latest |
| Animations | QPropertyAnimation | Built-in |

### Performance Optimization

```python
class OptimizedMainWindow(QMainWindow):
    """Performance-optimized main window."""
    
    def __init__(self):
        super().__init__()
        self._setup_optimizations()
    
    def _setup_optimizations(self):
        """Setup performance optimizations."""
        # Enable OpenGL rendering if available
        if QOpenGLContext.supportsThreadedOpenGL():
            QApplication.setAttribute(Qt.AA_UseOpenGLES)
        
        # Disable font antialiasing for better performance
        font = QFont("Roboto", 10)
        font.setStyleStrategy(QFont.NoAntialias)
        QApplication.setFont(font)
        
        # Use native dialogs
        QApplication.setAttribute(Qt.AA_NativeWindows)
    
    def paintEvent(self, event):
        """Optimized paint event."""
        # Only repaint changed regions
        painter = QPainter(self)
        painter.setClipRect(event.rect())
        
        # Draw only visible widgets
        for widget in self.findChildren(QWidget):
            if widget.isVisible() and event.rect().intersects(widget.geometry()):
                # Draw widget
                pass
```

---

## Customization

### User Preferences

```python
class GUICustomization:
    """Handle user UI customizations."""
    
    CUSTOMIZABLE_ELEMENTS = {
        "font_size": {"min": 10, "max": 24, "default": 14},
        "font_family": {"options": ["Roboto", "Arial", "System"]},
        "theme": {"options": ["light", "dark", "auto"]},
        "accent_color": {"options": ["blue", "green", "purple", "orange"]},
        "border_radius": {"min": 0, "max": 20, "default": 8},
        "animation_speed": {"min": 0, "max": 1000, "default": 300},
    }
    
    def apply_customization(self, element: str, value):
        """Apply user customization."""
        if element == "font_size":
            self._apply_font_size(value)
        elif element == "theme":
            self._apply_theme(value)
        elif element == "accent_color":
            self._apply_accent_color(value)
    
    def _apply_accent_color(self, color: str):
        """Apply custom accent color."""
        color_map = {
            "blue": "#2196F3",
            "green": "#4CAF50",
            "purple": "#9C27B0",
            "orange": "#FF9800",
        }
        
        accent = color_map.get(color, "#2196F3")
        
        # Update stylesheet with new accent
        stylesheet = f"""
            QPushButton {{
                background-color: {accent};
            }}
            QComboBox:focus {{
                border-color: {accent};
            }}
        """
        QApplication.instance().setStyleSheet(stylesheet)
```

### Custom Themes

```yaml
# custom_theme.yaml
theme:
  name: "Ocean"
  colors:
    primary: "#006994"
    secondary: "#00A8E8"
    background: "#E0F7FA"
    surface: "#FFFFFF"
    text: "#003945"
  fonts:
    primary: "Open Sans"
    monospace: "Fira Code"
  border_radius: 12
  animation_speed: 250
```

---

This modern GUI documentation ensures VoiceTranslate Pro provides an intuitive, beautiful, and accessible user experience across all platforms.
