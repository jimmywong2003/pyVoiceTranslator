# Real-Time Voice Translation Application - GUI Design Document

## 1. GUI Framework Recommendation

### Selected Framework: **PyQt6 / PySide6**

#### Justification

| Criteria | PyQt6/PySide6 | CustomTkinter | Tauri |
|----------|---------------|---------------|-------|
| **Real-time Performance** | Excellent - Direct hardware acceleration | Good - Limited by Tkinter | Moderate - WebView overhead |
| **Audio Visualization** | Native support via PyQtGraph | Requires external libraries | Canvas/WebGL based |
| **Cross-platform** | Windows, macOS (Intel/Apple Silicon), Linux | All platforms | All platforms |
| **Fluent Design** | Achievable with custom QSS | Limited theming | Native via CSS |
| **Development Speed** | Fast with Qt Designer | Very fast | Moderate |
| **Packaging** | PyInstaller, briefcase | PyInstaller | Complex build process |
| **Apple Silicon** | Native support via universal wheels | Native support | Native support |

#### Key Advantages for This Project:
1. **PyQtGraph Integration**: High-performance real-time plotting for waveform/spectrogram
2. **QAudioInput**: Native audio capture with low latency
3. **QThread**: Efficient background processing for audio/translation
4. **QSS Styling**: Complete control over Fluent Design implementation
5. **Mature Ecosystem**: Extensive documentation and community support

---

## 2. UI Layout Design

### Main Window Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [Logo]  Voice Translator                              [Min] [Max] [Close]  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────────────────────────────────────────┐  │
│  │   CONTROL   │  │           MAIN VISUALIZATION AREA                    │  │
│  │    PANEL    │  │  ┌───────────────────────────────────────────────┐  │  │
│  │             │  │  │         VOICE VISUALIZATION                    │  │  │
│  │ ┌─────────┐ │  │  │    [Waveform] [Spectrogram] [Volume]          │  │  │
│  │ │Language │ │  │  │                                                 │  │  │
│  │ │Selector │ │  │  │    ╭─────────────────────────────────────╮      │  │  │
│  │ │  🇨🇳→🇺🇸 │ │  │  │    │  ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿  │      │  │  │
│  │ └─────────┘ │  │  │    │  ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿  │      │  │  │
│  │             │  │  │    ╰─────────────────────────────────────╯      │  │  │
│  │ ┌─────────┐ │  │  │    [Segmentation Markers ▓▓░░▓▓▓░░░▓▓▓]         │  │  │
│  │ │  Mode   │ │  │  └───────────────────────────────────────────────┘  │  │
│  │ │ ☁️/⚡   │ │  │                                                      │  │
│  │ └─────────┘ │  │  ┌───────────────────────────────────────────────┐  │  │
│  │             │  │  │      REAL-TIME TRANSCRIPTION                   │  │  │
│  │ ┌─────────┐ │  │  │  "Hello, how are you today?"                   │  │  │
│  │ │  Audio  │ │  │  │  "你好，你今天怎么样？"                          │  │  │
│  │ │ Source  │ │  │  └───────────────────────────────────────────────┘  │  │
│  │ │ 🎤/🔊  │ │  │                                                      │  │
│  │ └─────────┘ │  │  ┌───────────────────────────────────────────────┐  │  │
│  │             │  │  │           VIDEO PLAYER (Optional)              │  │  │
│  │ ┌─────────┐ │  │  │    [Video Area with Subtitle Overlay]          │  │  │
│  │ │  Test   │ │  │  │                                                 │  │  │
│  │ │ Controls│ │  │  │    Subtitle: "Translated text appears here"    │  │  │
│  │ └─────────┘ │  │  └───────────────────────────────────────────────┘  │  │
│  │             │  │                                                      │  │
│  │ ┌─────────┐ │  └─────────────────────────────────────────────────────┘  │
│  │ │ System  │ │                                                           │
│  │ │ Status  │ │                                                           │
│  │ │ CPU: 45%│ │                                                           │
│  │ │ RAM: 2GB│ │                                                           │
│  │ └─────────┘ │                                                           │
│  └─────────────┘                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Status: Recording... | Model: Whisper-Large-V3 | Latency: 245ms           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Specifications

#### 2.1 Control Panel (Left Sidebar - 280px width)

| Component | Type | Description |
|-----------|------|-------------|
| **Language Selector** | Custom ComboBox | Dual dropdown for source/target languages with flag icons |
| **Mode Toggle** | Animated Switch | Edge (local) vs Cloud processing mode |
| **Audio Source** | Segmented Button | Microphone / System Audio toggle |
| **Test Controls** | Button Group | Audio Test, Load Video, Benchmark |
| **System Monitor** | Mini Dashboard | CPU/RAM usage with progress bars |
| **Settings Button** | Icon Button | Opens settings dialog |

#### 2.2 Main Visualization Area

| Component | Type | Description |
|-----------|------|-------------|
| **Visualization Tabs** | Tab Bar | Waveform / Spectrogram / Volume Meter |
| **Voice Waveform** | PyQtGraph Plot | Real-time amplitude visualization |
| **Spectrogram** | PyQtGraph ImageItem | Frequency vs time heatmap |
| **Volume Meter** | Custom Widget | Vertical bar with color gradient |
| **Segmentation Bar** | Timeline Widget | Visual voice activity detection markers |

#### 2.3 Transcription Display

| Component | Type | Description |
|-----------|------|-------------|
| **Source Text** | Scrollable Label | Original transcription with timestamps |
| **Translated Text** | Scrollable Label | Translated output with confidence score |
| **Copy Button** | Icon Button | Copy text to clipboard |
| **Export Button** | Icon Button | Save transcription to file |

#### 2.4 Video Player (Optional Panel)

| Component | Type | Description |
|-----------|------|-------------|
| **Video View** | QVideoWidget | Video playback with subtitle overlay |
| **Subtitle Overlay** | QLabel | Semi-transparent subtitle display |
| **Playback Controls** | Control Bar | Play/Pause, Seek, Volume |
| **Load Video Button** | Button | File picker for test videos |

---

## 3. Voice Visualization Implementation

### 3.1 Architecture

```
Audio Input → Audio Buffer → Processing Thread → Visualization Update
                    ↓
            Voice Activity Detection → Segmentation Data
```

### 3.2 Waveform Visualization

```python
# Core implementation approach
class WaveformWidget(pg.PlotWidget):
    def __init__(self):
        super().__init__()
        self.plot_item = self.getPlotItem()
        self.curve = self.plot_item.plot(pen=pg.mkPen(color='#0078D4', width=2))
        self.data = np.zeros(1024)
        
    def update_waveform(self, audio_buffer: np.ndarray):
        # Apply smoothing
        self.data = np.roll(self.data, -len(audio_buffer))
        self.data[-len(audio_buffer):] = audio_buffer
        self.curve.setData(self.data)
```

### 3.3 Spectrogram Visualization

```python
class SpectrogramWidget(pg.GraphicsLayoutWidget):
    def __init__(self):
        super().__init__()
        self.img_item = pg.ImageItem()
        self.addItem(self.img_item)
        # Color map: deep blue to cyan to yellow to red
        self.color_map = pg.ColorMap(
            pos=[0, 0.25, 0.5, 0.75, 1],
            color=[(0,0,50), (0,100,255), (0,255,255), (255,255,0), (255,0,0)]
        )
        self.img_item.setColorMap(self.color_map)
        
    def update_spectrogram(self, fft_data: np.ndarray):
        # Rolling buffer for time axis
        self.spectrogram_data = np.roll(self.spectrogram_data, -1, axis=0)
        self.spectrogram_data[-1] = fft_data
        self.img_item.setImage(self.spectrogram_data.T)
```

### 3.4 Volume Meter

```python
class VolumeMeter(QWidget):
    def __init__(self):
        super().__init__()
        self.volume = 0
        self.gradient = QLinearGradient(0, self.height(), 0, 0)
        self.gradient.setColorAt(0.0, QColor('#107C10'))    # Green
        self.gradient.setColorAt(0.6, QColor('#FFB900'))    # Yellow
        self.gradient.setColorAt(1.0, QColor('#D13438'))    # Red
        
    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw background
        painter.fillRect(self.rect(), QColor('#F3F2F1'))
        # Draw volume bar
        bar_height = int(self.height() * self.volume)
        painter.fillRect(0, self.height() - bar_height, 
                        self.width(), bar_height, self.gradient)
```

### 3.5 Voice Segmentation Visualization

```python
class SegmentationTimeline(QWidget):
    def __init__(self):
        super().__init__()
        self.segments = []  # List of (start_time, end_time, is_speech)
        self.colors = {
            'speech': QColor('#0078D4'),
            'silence': QColor('#E1DFDD'),
            'processing': QColor('#FFB900')
        }
        
    def add_segment(self, start: float, end: float, segment_type: str):
        self.segments.append((start, end, segment_type))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        width = self.width()
        total_duration = self.get_total_duration()
        
        for start, end, seg_type in self.segments:
            x1 = int((start / total_duration) * width)
            x2 = int((end / total_duration) * width)
            painter.fillRect(x1, 0, x2 - x1, self.height(), 
                           self.colors[seg_type])
```

---

## 4. Modern Styling Implementation (Fluent Design)

### 4.1 Color Palette

```python
# Microsoft Edge / Fluent Design Colors
FLUENT_COLORS = {
    # Primary
    'primary': '#0078D4',
    'primary_dark': '#106EBE',
    'primary_light': '#2B88D8',
    
    # Background
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#F3F2F1',
    'bg_tertiary': '#FAF9F8',
    
    # Surface
    'surface': '#FFFFFF',
    'surface_hover': '#F3F2F1',
    'surface_pressed': '#EDEBE9',
    
    # Text
    'text_primary': '#323130',
    'text_secondary': '#605E5C',
    'text_disabled': '#A19F9D',
    
    # Accent
    'accent': '#0078D4',
    'accent_hover': '#106EBE',
    'accent_pressed': '#005A9E',
    
    # Status
    'success': '#107C10',
    'warning': '#FFB900',
    'error': '#D13438',
    'info': '#0078D4',
    
    # Border
    'border': '#E1DFDD',
    'border_focus': '#0078D4',
    
    # Shadow
    'shadow': 'rgba(0, 0, 0, 0.08)',
    'shadow_strong': 'rgba(0, 0, 0, 0.16)',
}
```

### 4.2 Typography

```python
FLUENT_TYPOGRAPHY = {
    'font_family': 'Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif',
    'title': {'size': 24, 'weight': 600},
    'subtitle': {'size': 18, 'weight': 600},
    'body': {'size': 14, 'weight': 400},
    'body_strong': {'size': 14, 'weight': 600},
    'caption': {'size': 12, 'weight': 400},
    'caption_strong': {'size': 12, 'weight': 600},
}
```

### 4.3 QSS Stylesheet

```qss
/* Main Window */
QMainWindow {
    background-color: #F3F2F1;
    font-family: "Segoe UI", sans-serif;
}

/* Buttons - Fluent Style */
QPushButton {
    background-color: #FFFFFF;
    color: #323130;
    border: 1px solid #E1DFDD;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 400;
}

QPushButton:hover {
    background-color: #F3F2F1;
    border-color: #8A8886;
}

QPushButton:pressed {
    background-color: #EDEBE9;
}

QPushButton:disabled {
    background-color: #F3F2F1;
    color: #A19F9D;
    border-color: #E1DFDD;
}

/* Primary Button */
QPushButton.primary {
    background-color: #0078D4;
    color: #FFFFFF;
    border: none;
}

QPushButton.primary:hover {
    background-color: #106EBE;
}

QPushButton.primary:pressed {
    background-color: #005A9E;
}

/* ComboBox */
QComboBox {
    background-color: #FFFFFF;
    color: #323130;
    border: 1px solid #E1DFDD;
    border-radius: 4px;
    padding: 8px 12px;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #8A8886;
}

QComboBox:focus {
    border-color: #0078D4;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: url(:/icons/chevron-down.svg);
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #E1DFDD;
    border-radius: 4px;
    selection-background-color: #F3F2F1;
    selection-color: #323130;
}

/* Slider */
QSlider::groove:horizontal {
    height: 4px;
    background: #E1DFDD;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #0078D4;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 1px solid #8A8886;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}

QSlider::handle:horizontal:hover {
    border-color: #0078D4;
}

/* Progress Bar */
QProgressBar {
    background-color: #E1DFDD;
    border-radius: 4px;
    height: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0078D4;
    border-radius: 4px;
}

QProgressBar::chunk:disabled {
    background-color: #A19F9D;
}

/* ScrollBar */
QScrollBar:vertical {
    background-color: transparent;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #8A8886;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #605E5C;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Tab Widget */
QTabWidget::pane {
    border: none;
    background-color: #FFFFFF;
}

QTabBar::tab {
    background-color: transparent;
    color: #605E5C;
    padding: 12px 20px;
    border: none;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #0078D4;
    border-bottom: 2px solid #0078D4;
}

QTabBar::tab:hover:!selected {
    color: #323130;
}

/* Group Box */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E1DFDD;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #323130;
}

/* Line Edit */
QLineEdit {
    background-color: #FFFFFF;
    color: #323130;
    border: 1px solid #E1DFDD;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 14px;
}

QLineEdit:focus {
    border-color: #0078D4;
}

QLineEdit:disabled {
    background-color: #F3F2F1;
    color: #A19F9D;
}
```

### 4.4 Animations

```python
class FluentAnimation:
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 200):
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()
        
    @staticmethod
    def slide_in(widget: QWidget, direction: str = 'left', duration: int = 300):
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        # Implementation depends on direction
        animation.start()
        
    @staticmethod
    def pulse(widget: QWidget, duration: int = 1000):
        animation = QPropertyAnimation(widget, b"scale")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(1.05)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.setLoopCount(-1)  # Infinite
        animation.start()
```

---

## 5. Component Architecture

### 5.1 Module Structure

```
gui/
├── __init__.py
├── main_window.py          # Main application window
├── app.py                  # Application entry point
│
├── components/
│   ├── __init__.py
│   ├── control_panel.py    # Left sidebar controls
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── waveform.py     # Waveform display
│   │   ├── spectrogram.py  # Spectrogram display
│   │   ├── volume_meter.py # Volume indicator
│   │   └── segmentation.py # Voice segmentation timeline
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── display.py      # Transcription text display
│   │   └── subtitle_overlay.py  # Video subtitle overlay
│   ├── video/
│   │   ├── __init__.py
│   │   ├── player.py       # Video player widget
│   │   └── controls.py     # Playback controls
│   ├── system/
│   │   ├── __init__.py
│   │   ├── cpu_monitor.py  # CPU usage display
│   │   └── status_bar.py   # Bottom status bar
│   └── common/
│       ├── __init__.py
│       ├── fluent_button.py
│       ├── fluent_combo.py
│       ├── fluent_toggle.py
│       └── fluent_slider.py
│
├── styles/
│   ├── __init__.py
│   ├── colors.py           # Color definitions
│   ├── typography.py       # Font definitions
│   ├── animations.py       # Animation utilities
│   └── main.qss            # Main stylesheet
│
├── dialogs/
│   ├── __init__.py
│   ├── settings.py         # Settings dialog
│   ├── audio_test.py       # Audio detection test
│   └── about.py            # About dialog
│
└── utils/
    ├── __init__.py
    ├── theme_manager.py    # Theme switching
    └── icon_provider.py    # Icon management
```

### 5.2 Class Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        MainWindow                               │
├─────────────────────────────────────────────────────────────────┤
│ - control_panel: ControlPanel                                   │
│ - visualization_area: VisualizationArea                         │
│ - transcription_display: TranscriptionDisplay                   │
│ - video_player: VideoPlayer                                     │
│ - status_bar: StatusBar                                         │
├─────────────────────────────────────────────────────────────────┤
│ + setup_ui()                                                    │
│ + connect_signals()                                             │
│ + apply_styles()                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────┐
│ ControlPanel  │    │VisualizationArea│    │Transcription │
├───────────────┤    ├─────────────────┤    │   Display    │
│ - language_sel│    │ - waveform      │    ├──────────────┤
│ - mode_toggle │    │ - spectrogram   │    │ - source_text│
│ - audio_source│    │ - volume_meter  │    │ - trans_text │
│ - test_btn    │    │ - segmentation  │    │ - copy_btn   │
│ - cpu_monitor │    ├─────────────────┤    │ - export_btn │
├───────────────┤    │ + switch_view() │    ├──────────────┤
│ + update_lang │    │ + update_data() │    │ + add_text() │
│ + toggle_mode │    └─────────────────┘    │ + clear()    │
└───────────────┘                           └──────────────┘
```

### 5.3 Signal/Slot Architecture

```python
# signals.py
from PyQt6.QtCore import QObject, pyqtSignal

class AppSignals(QObject):
    # Audio signals
    audio_data = pyqtSignal(np.ndarray)  # Raw audio buffer
    audio_level = pyqtSignal(float)       # Volume level 0-1
    
    # Voice activity
    speech_start = pyqtSignal(float)      # Timestamp
    speech_end = pyqtSignal(float)        # Timestamp
    
    # Transcription
    transcription_ready = pyqtSignal(str, str, float)  # text, lang, confidence
    translation_ready = pyqtSignal(str, str)           # text, lang
    
    # System
    cpu_usage = pyqtSignal(float)
    memory_usage = pyqtSignal(float)
    
    # UI
    language_changed = pyqtSignal(str, str)  # source, target
    mode_changed = pyqtSignal(str)           # 'edge' or 'cloud'
    audio_source_changed = pyqtSignal(str)   # 'mic' or 'system'
    
    # Video
    video_loaded = pyqtSignal(str)
    subtitle_update = pyqtSignal(str, float)  # text, timestamp

# Global signals instance
app_signals = AppSignals()
```

---

## 6. Responsive Design Considerations

### 6.1 Layout Strategy

```python
class ResponsiveLayout:
    """Handles responsive layout adjustments"""
    
    BREAKPOINTS = {
        'compact': 800,      # Hide video panel
        'medium': 1200,      # Collapse sidebar
        'large': 1600,       # Full layout
    }
    
    def __init__(self, main_window: QMainWindow):
        self.window = main_window
        self.current_mode = 'large'
        
    def on_resize(self, width: int):
        if width < self.BREAKPOINTS['compact']:
            self.set_compact_mode()
        elif width < self.BREAKPOINTS['medium']:
            self.set_medium_mode()
        else:
            self.set_large_mode()
            
    def set_compact_mode(self):
        # Hide video panel
        # Stack transcription below visualization
        # Collapse sidebar to icons only
        pass
        
    def set_medium_mode(self):
        # Show video in overlay mode
        # Side-by-side transcription
        # Expanded sidebar
        pass
        
    def set_large_mode(self):
        # Full layout as designed
        pass
```

### 6.2 Scaling Strategy

```python
class ScalingManager:
    """Manages DPI scaling for different displays"""
    
    def __init__(self):
        self.base_dpi = 96
        self.scale_factor = self.calculate_scale()
        
    def calculate_scale(self) -> float:
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()
        return dpi / self.base_dpi
        
    def scale(self, value: int) -> int:
        return int(value * self.scale_factor)
        
    def scale_font(self, size: int) -> int:
        return self.scale(size)
```

### 6.3 Platform-Specific Adjustments

```python
class PlatformAdapter:
    """Handles platform-specific UI adjustments"""
    
    @staticmethod
    def get_title_bar_height() -> int:
        if sys.platform == 'darwin':
            return 28  # macOS traffic lights
        return 0  # Windows custom title bar
        
    @staticmethod
    def get_window_buttons() -> list:
        if sys.platform == 'darwin':
            return []  # Native buttons
        return ['minimize', 'maximize', 'close']
        
    @staticmethod
    def get_font_family() -> str:
        if sys.platform == 'darwin':
            return '-apple-system, BlinkMacSystemFont, "Segoe UI"'
        return '"Segoe UI", sans-serif'
```

---

## 7. Code Structure for GUI Module

### 7.1 Main Application Entry

```python
# gui/app.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from .main_window import MainWindow
from .styles.colors import FLUENT_COLORS
from .utils.theme_manager import ThemeManager

class VoiceTranslatorApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Voice Translator")
        self.setOrganizationName("YourCompany")
        
        # Enable high DPI scaling
        self.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        # Initialize theme
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_theme('light')
        
        # Create main window
        self.main_window = MainWindow()
        self.main_window.show()
        
    def run(self):
        return self.exec()

def main():
    app = VoiceTranslatorApp(sys.argv)
    return app.run()

if __name__ == '__main__':
    sys.exit(main())
```

### 7.2 Main Window Implementation

```python
# gui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar
)
from PyQt6.QtCore import Qt

from .components.control_panel import ControlPanel
from .components.visualization.area import VisualizationArea
from .components.transcription.display import TranscriptionDisplay
from .components.video.player import VideoPlayer
from .components.system.status_bar import CustomStatusBar
from .signals import app_signals

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Translator")
        self.setMinimumSize(1000, 700)
        self.resize(1400, 900)
        
        self.setup_ui()
        self.connect_signals()
        self.apply_styles()
        
    def setup_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Control panel (left)
        self.control_panel = ControlPanel()
        self.control_panel.setFixedWidth(280)
        splitter.addWidget(self.control_panel)
        
        # Main content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # Visualization area
        self.visualization_area = VisualizationArea()
        content_layout.addWidget(self.visualization_area, stretch=2)
        
        # Transcription display
        self.transcription_display = TranscriptionDisplay()
        content_layout.addWidget(self.transcription_display, stretch=1)
        
        # Video player (optional)
        self.video_player = VideoPlayer()
        self.video_player.setVisible(False)
        content_layout.addWidget(self.video_player, stretch=2)
        
        splitter.addWidget(content_widget)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = CustomStatusBar()
        self.setStatusBar(self.status_bar)
        
    def connect_signals(self):
        # Control panel signals
        self.control_panel.language_changed.connect(
            app_signals.language_changed.emit
        )
        self.control_panel.mode_toggled.connect(
            app_signals.mode_changed.emit
        )
        self.control_panel.audio_source_changed.connect(
            app_signals.audio_source_changed.emit
        )
        
        # System signals
        app_signals.cpu_usage.connect(self.status_bar.update_cpu)
        app_signals.memory_usage.connect(self.status_bar.update_memory)
        
        # Transcription signals
        app_signals.transcription_ready.connect(
            self.transcription_display.add_source_text
        )
        app_signals.translation_ready.connect(
            self.transcription_display.add_translated_text
        )
        
    def apply_styles(self):
        with open('gui/styles/main.qss', 'r') as f:
            self.setStyleSheet(f.read())
            
    def toggle_video_panel(self, show: bool):
        self.video_player.setVisible(show)
```

### 7.3 Control Panel Implementation

```python
# gui/components/control_panel.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QProgressBar
)
from PyQt6.QtCore import pyqtSignal

from .common.fluent_toggle import FluentToggle
from .common.fluent_combo import FluentComboBox
from .common.fluent_button import FluentButton
from ..styles.colors import FLUENT_COLORS

class ControlPanel(QWidget):
    # Signals
    language_changed = pyqtSignal(str, str)
    mode_toggled = pyqtSignal(str)
    audio_source_changed = pyqtSignal(str)
    test_clicked = pyqtSignal()
    video_load_clicked = pyqtSignal()
    
    LANGUAGES = {
        'zh': ('🇨🇳', 'Chinese'),
        'en': ('🇺🇸', 'English'),
        'ja': ('🇯🇵', 'Japanese'),
        'fr': ('🇫🇷', 'French'),
    }
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Voice Translator")
        header.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {FLUENT_COLORS['text_primary']};
        """)
        layout.addWidget(header)
        
        # Language Selection Group
        lang_group = QGroupBox("Languages")
        lang_layout = QVBoxLayout(lang_group)
        
        # Source language
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("From:"))
        self.source_lang = FluentComboBox()
        self._populate_languages(self.source_lang)
        self.source_lang.setCurrentIndex(0)  # Chinese
        source_layout.addWidget(self.source_lang)
        lang_layout.addLayout(source_layout)
        
        # Target language
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("To:"))
        self.target_lang = FluentComboBox()
        self._populate_languages(self.target_lang)
        self.target_lang.setCurrentIndex(1)  # English
        target_layout.addWidget(self.target_lang)
        lang_layout.addLayout(target_layout)
        
        layout.addWidget(lang_group)
        
        # Processing Mode Group
        mode_group = QGroupBox("Processing Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        mode_label_layout = QHBoxLayout()
        self.mode_label = QLabel("⚡ Edge (Local)")
        mode_label_layout.addWidget(self.mode_label)
        mode_label_layout.addStretch()
        mode_layout.addLayout(mode_label_layout)
        
        self.mode_toggle = FluentToggle()
        self.mode_toggle.toggled.connect(self._on_mode_toggle)
        mode_layout.addWidget(self.mode_toggle)
        
        layout.addWidget(mode_group)
        
        # Audio Source Group
        audio_group = QGroupBox("Audio Source")
        audio_layout = QVBoxLayout(audio_group)
        
        self.audio_source = FluentComboBox()
        self.audio_source.addItem("🎤 Microphone", "mic")
        self.audio_source.addItem("🔊 System Audio", "system")
        self.audio_source.currentIndexChanged.connect(
            lambda: self.audio_source_changed.emit(
                self.audio_source.currentData()
            )
        )
        audio_layout.addWidget(self.audio_source)
        
        layout.addWidget(audio_group)
        
        # Test Controls Group
        test_group = QGroupBox("Testing")
        test_layout = QVBoxLayout(test_group)
        
        self.test_btn = FluentButton("🎵 Audio Test", primary=True)
        self.test_btn.clicked.connect(self.test_clicked.emit)
        test_layout.addWidget(self.test_btn)
        
        self.video_btn = FluentButton("🎬 Load Video")
        self.video_btn.clicked.connect(self.video_load_clicked.emit)
        test_layout.addWidget(self.video_btn)
        
        layout.addWidget(test_group)
        
        # System Monitor Group
        monitor_group = QGroupBox("System Status")
        monitor_layout = QVBoxLayout(monitor_group)
        
        # CPU
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(QLabel("CPU:"))
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setTextVisible(True)
        cpu_layout.addWidget(self.cpu_bar)
        monitor_layout.addLayout(cpu_layout)
        
        # Memory
        mem_layout = QHBoxLayout()
        mem_layout.addWidget(QLabel("RAM:"))
        self.mem_bar = QProgressBar()
        self.mem_bar.setRange(0, 100)
        self.mem_bar.setValue(0)
        self.mem_bar.setTextVisible(True)
        mem_layout.addWidget(self.mem_bar)
        monitor_layout.addLayout(mem_layout)
        
        layout.addWidget(monitor_group)
        
        # Spacer
        layout.addStretch()
        
        # Settings button
        self.settings_btn = FluentButton("⚙️ Settings")
        layout.addWidget(self.settings_btn)
        
    def _populate_languages(self, combo: FluentComboBox):
        for code, (flag, name) in self.LANGUAGES.items():
            combo.addItem(f"{flag} {name}", code)
            
    def _on_mode_toggle(self, checked: bool):
        mode = 'cloud' if checked else 'edge'
        label = "☁️ Cloud" if checked else "⚡ Edge (Local)"
        self.mode_label.setText(label)
        self.mode_toggled.emit(mode)
        
    def update_cpu(self, usage: float):
        self.cpu_bar.setValue(int(usage))
        # Color based on usage
        if usage > 80:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #D13438; }")
        elif usage > 60:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #FFB900; }")
        else:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #107C10; }")
            
    def update_memory(self, usage: float):
        self.mem_bar.setValue(int(usage))
```

### 7.4 Visualization Area Implementation

```python
# gui/components/visualization/area.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QButtonGroup
)
from PyQt6.QtCore import Qt

from .waveform import WaveformWidget
from .spectrogram import SpectrogramWidget
from .volume_meter import VolumeMeter
from .segmentation import SegmentationTimeline
from ...signals import app_signals

class VisualizationArea(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # View selector tabs
        self.tab_widget = QTabWidget()
        
        # Waveform tab
        self.waveform = WaveformWidget()
        self.tab_widget.addTab(self.waveform, "∿ Waveform")
        
        # Spectrogram tab
        self.spectrogram = SpectrogramWidget()
        self.tab_widget.addTab(self.spectrogram, "▓ Spectrogram")
        
        # Volume meter tab
        volume_container = QWidget()
        volume_layout = QHBoxLayout(volume_container)
        volume_layout.addStretch()
        self.volume_meter = VolumeMeter()
        self.volume_meter.setFixedSize(60, 200)
        volume_layout.addWidget(self.volume_meter)
        volume_layout.addStretch()
        self.tab_widget.addTab(volume_container, "📊 Volume")
        
        layout.addWidget(self.tab_widget, stretch=4)
        
        # Segmentation timeline
        self.segmentation = SegmentationTimeline()
        self.segmentation.setFixedHeight(40)
        layout.addWidget(self.segmentation, stretch=1)
        
    def connect_signals(self):
        app_signals.audio_data.connect(self._on_audio_data)
        app_signals.audio_level.connect(self._on_audio_level)
        app_signals.speech_start.connect(self._on_speech_start)
        app_signals.speech_end.connect(self._on_speech_end)
        
    def _on_audio_data(self, data):
        self.waveform.update_data(data)
        self.spectrogram.update_data(data)
        
    def _on_audio_level(self, level: float):
        self.volume_meter.set_level(level)
        
    def _on_speech_start(self, timestamp: float):
        self.segmentation.add_marker(timestamp, 'speech_start')
        
    def _on_speech_end(self, timestamp: float):
        self.segmentation.add_marker(timestamp, 'speech_end')
```

### 7.5 Custom Fluent Components

```python
# gui/components/common/fluent_toggle.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QBrush

class FluentToggle(QWidget):
    """Microsoft Fluent Design toggle switch"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._animation = None
        self._thumb_pos = 4  # Starting position
        
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    @property
    def checked(self) -> bool:
        return self._checked
        
    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._animate_thumb()
            self.toggled.emit(checked)
            
    def _animate_thumb(self):
        target_pos = 24 if self._checked else 4
        self._animation = QPropertyAnimation(self, b"thumb_pos")
        self._animation.setDuration(150)
        self._animation.setStartValue(self._thumb_pos)
        self._animation.setEndValue(target_pos)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animation.start()
        
    def get_thumb_pos(self):
        return self._thumb_pos
        
    def set_thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()
        
    thumb_pos = property(get_thumb_pos, set_thumb_pos)
    
    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        bg_color = QColor('#0078D4') if self._checked else QColor('#E1DFDD')
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)
        
        # Thumb
        thumb_color = QColor('#FFFFFF')
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(int(self._thumb_pos), 2, 20, 20)
        
        painter.end()
```

---

## 8. Dependencies

### requirements.txt

```
# Core GUI
PyQt6>=6.4.0
PyQt6-Qt6>=6.4.0

# Visualization
pyqtgraph>=0.13.0
numpy>=1.23.0

# Audio
PyAudio>=0.2.13
librosa>=0.10.0
soundfile>=0.12.0

# Video
PyQt6-multimedia>=6.4.0

# System monitoring
psutil>=5.9.0

# Utilities
pillow>=9.0.0
```

---

## 9. Build & Distribution

### 9.1 Windows Build

```bash
# Using PyInstaller
pyinstaller --name="VoiceTranslator" \
    --windowed \
    --icon=assets/icon.ico \
    --add-data="gui/styles;gui/styles" \
    --add-data="assets;assets" \
    --hidden-import=PyQt6.sip \
    main.py
```

### 9.2 macOS Build (Universal)

```bash
# Using briefcase (BeeWare)
briefcase create
briefcase build
briefcase package --sign

# Or PyInstaller with universal2
pyinstaller --name="VoiceTranslator" \
    --windowed \
    --icon=assets/icon.icns \
    --target-architecture universal2 \
    main.py
```

---

## Summary

This design provides a comprehensive, modern GUI for a real-time voice translation application using **PyQt6/PySide6** with:

1. **Fluent Design styling** matching Microsoft Edge aesthetics
2. **High-performance visualizations** using PyQtGraph for waveform/spectrogram
3. **Modular architecture** for easy maintenance and extension
4. **Cross-platform support** for Windows and macOS (Apple Silicon)
5. **Responsive design** adapting to different screen sizes
6. **Smooth animations** and professional UI interactions

The framework choice of PyQt6 provides the best balance of performance, features, and cross-platform compatibility for this real-time audio application.
