# Real-Time Voice Translation System Architecture
## Comprehensive Design Document

**Version:** 1.0  
**Date:** 2024  
**Target Platforms:** Windows, macOS (Apple Silicon M1 Pro)  
**Supported Languages:** Chinese, English, Japanese, French

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [System Block Diagram](#2-system-block-diagram)
3. [Component Architecture](#3-component-architecture)
4. [Data Flow & Workflow](#4-data-flow--workflow)
5. [Module Breakdown](#5-module-breakdown)
6. [Interface Definitions](#6-interface-definitions)
7. [Technology Stack](#7-technology-stack)
8. [Design Document Structure](#8-design-document-structure)

---

## 1. Executive Summary

This document presents the comprehensive system architecture for a real-time voice translation application featuring:
- Edge-first voice detection and segmentation
- Hybrid edge/cloud speech recognition and translation
- Multi-source audio input (microphone/system audio)
- Modern GUI with real-time visualization
- Performance monitoring and benchmarking
- Cross-platform support (Windows/macOS)

---

## 2. System Block Diagram

### 2.1 High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           REAL-TIME VOICE TRANSLATION SYSTEM                            │
│                              (Windows / macOS M1 Pro)                                   │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           PRESENTATION LAYER (GUI)                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │   Main      │  │   Voice     │  │  Segment    │  │   Performance/CPU       │ │   │
│  │  │   Window    │  │Visualizer   │  │  Timeline   │  │   Monitor Panel         │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────────┘ │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │   Source    │  │ Translation │  │   Subtitle  │  │   Settings/Config       │ │   │
│  │  │  Selector   │  │   Display   │  │   Overlay   │  │   Panel                 │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         APPLICATION CORE LAYER                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐  │   │
│  │  │  Audio Capture  │  │  Audio Buffer   │  │      Configuration Manager      │  │   │
│  │  │    Manager      │  │    Manager      │  │        (Settings/Profiles)      │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐  │   │
│  │  │  State Machine  │  │  Event Bus      │  │      Performance Profiler       │  │   │
│  │  │    Controller   │  │  (Pub/Sub)      │  │        (CPU/Benchmark)          │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                    ┌─────────────────────┴─────────────────────┐                        │
│                    ▼                                           ▼                        │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────┐            │
│  │      EDGE PROCESSING LAYER      │    │      CLOUD PROCESSING LAYER     │            │
│  │  ┌─────────────────────────┐    │    │  ┌─────────────────────────┐    │            │
│  │  │   Voice Activity        │    │    │  │   Cloud ASR Service     │    │            │
│  │  │   Detection (VAD)       │    │    │  │   (Optional Fallback)   │    │            │
│  │  └─────────────────────────┘    │    │  └─────────────────────────┘    │            │
│  │  ┌─────────────────────────┐    │    │  ┌─────────────────────────┐    │            │
│  │  │   Audio Segmentation    │    │    │  │   Cloud Translation     │    │            │
│  │  │   Engine                │    │    │  │   Service (Optional)    │    │            │
│  │  └─────────────────────────┘    │    │  └─────────────────────────┘    │            │
│  │  ┌─────────────────────────┐    │    │                                 │            │
│  │  │   Local ASR Engine      │    │    │                                 │            │
│  │  │   (Whisper/Other)       │    │    │                                 │            │
│  │  └─────────────────────────┘    │    │                                 │            │
│  │  ┌─────────────────────────┐    │    │                                 │            │
│  │  │   Local Translation     │    │    │                                 │            │
│  │  │   Engine (Argos/Opus)   │    │    │                                 │            │
│  │  └─────────────────────────┘    │    │                                 │            │
│  └─────────────────────────────────┘    └─────────────────────────────────┘            │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         AUDIO INPUT LAYER                                       │   │
│  │  ┌─────────────────────────┐    ┌─────────────────────────────────────────┐      │   │
│  │  │   Microphone Input      │    │   System Audio Capture                  │      │   │
│  │  │   (DirectSound/CoreAudio)│   │   (WASAPI/Loopback/BlackHole)           │      │   │
│  │  └─────────────────────────┘    └─────────────────────────────────────────┘      │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐      │   │
│  │  │                    Audio Input Test/Calibration Module                  │      │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Deployment Architecture (Edge vs Cloud Hybrid)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              HYBRID PROCESSING MODES                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌─────────────────────────────────┐     ┌─────────────────────────────────┐          │
│   │      EDGE-ONLY MODE             │     │      CLOUD-HYBRID MODE          │          │
│   │      (Offline/Privacy)          │     │      (Online/Accuracy)          │          │
│   │                                 │     │                                 │          │
│   │  ┌──────────┐   ┌──────────┐   │     │  ┌──────────┐   ┌──────────┐   │          │
│   │  │  Audio   │──▶│   VAD    │   │     │  │  Audio   │──▶│   VAD    │   │          │
│   │  │  Input   │   │  (Edge)  │   │     │  │  Input   │   │  (Edge)  │   │          │
│   │  └──────────┘   └────┬─────┘   │     │  └──────────┘   └────┬─────┘   │          │
│   │                      ▼          │     │                      ▼          │          │
│   │              ┌──────────────┐   │     │              ┌──────────────┐   │          │
│   │              │ Segmentation │   │     │              │ Segmentation │   │          │
│   │              │   (Edge)     │   │     │              │   (Edge)     │   │          │
│   │              └──────┬───────┘   │     │              └──────┬───────┘   │          │
│   │                     ▼           │     │                     ▼           │          │
│   │           ┌─────────────────┐   │     │           ┌─────────────────┐   │          │
│   │           │  Local ASR      │   │     │           │  Cloud ASR API  │   │          │
│   │           │  (Whisper.cpp)  │   │     │           │  (REST/WebSocket)│  │          │
│   │           └────────┬────────┘   │     │           └────────┬────────┘   │          │
│   │                    ▼            │     │                    │            │          │
│   │           ┌─────────────────┐   │     │                    │            │          │
│   │           │ Local Translate │   │     │                    ▼            │          │
│   │           │ (Argos/OpusMT)  │   │     │           ┌─────────────────┐   │          │
│   │           └────────┬────────┘   │     │           │ Cloud Translate │   │          │
│   │                    ▼            │     │           │    API          │   │          │
│   │           ┌─────────────────┐   │     │           └────────┬────────┘   │          │
│   │           │  GUI Display    │   │     │                    │            │          │
│   │           └─────────────────┘   │     │                    ▼            │          │
│   │                                 │     │           ┌─────────────────┐   │          │
│   │  ┌─────────────────────────┐    │     │           │  GUI Display    │   │          │
│   │  │  Latency: 100-300ms     │    │     │           └─────────────────┘   │          │
│   │  │  Privacy: High          │    │     │                                 │          │
│   │  │  Internet: Not Required │    │     │  ┌─────────────────────────┐    │          │
│   │  └─────────────────────────┘    │     │  │  Latency: 200-800ms     │    │          │
│   │                                 │     │  │  Privacy: Low-Medium    │    │          │
│   └─────────────────────────────────┘     │  │  Internet: Required     │    │          │
│                                           │  └─────────────────────────┘    │          │
│                                           │                                 │          │
│                                           └─────────────────────────────────┘          │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Architecture

### 3.1 Detailed Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           COMPONENT ARCHITECTURE                                        │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           GUI FRAMEWORK (PyQt6/PySide6)                         │   │
│  │                    Microsoft Edge Theme Style (Modern UI)                       │   │
│  ├─────────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                                 │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │   │
│  │   │  MainWindow  │  │ VoiceWaveform│  │SegmentView   │  │ SettingsDlg  │       │   │
│  │   │  Controller  │  │  Widget      │  │  Widget      │  │              │       │   │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │   │
│  │          │                 │                 │                 │               │   │
│  │          └─────────────────┴─────────────────┴─────────────────┘               │   │
│  │                            │                                                   │   │
│  │                            ▼                                                   │   │
│  │                   ┌─────────────────┐                                          │   │
│  │                   │  Theme Engine   │                                          │   │
│  │                   │  (QSS/Styles)   │                                          │   │
│  │                   └─────────────────┘                                          │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           CORE SERVICES                                         │   │
│  ├─────────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                                 │   │
│  │  ┌─────────────────────────┐      ┌─────────────────────────┐                  │   │
│  │  │    AudioService         │◄────►│    ConfigService        │                  │   │
│  │  │  - capture_audio()      │      │  - load_settings()      │                  │   │
│  │  │  - switch_source()      │      │  - save_profile()       │                  │   │
│  │  │  - test_input()         │      │  - get_language_cfg()   │                  │   │
│  │  └───────────┬─────────────┘      └─────────────────────────┘                  │   │
│  │              │                                                                  │   │
│  │              │  ┌─────────────────────────┐      ┌─────────────────────────┐    │   │
│  │              └──►    VADService           │◄────►│   TranslationService    │    │   │
│  │                 │  - detect_voice()       │      │  - translate_text()     │    │   │
│  │                 │  - segment_audio()      │      │  - switch_engine()      │    │   │
│  │                 │  - get_segments()       │      │  - get_supported_langs()│    │   │
│  │                 └───────────┬─────────────┘      └─────────────────────────┘    │   │
│  │                             │                                                   │   │
│  │                             │  ┌─────────────────────────┐                      │   │
│  │                             └──►    ASRService          │                      │   │
│  │                                │  - transcribe()         │                      │   │
│  │                                │  - switch_model()       │                      │   │
│  │                                │  - get_models()         │                      │   │
│  │                                └─────────────────────────┘                      │   │
│  │                                                                                 │   │
│  │  ┌─────────────────────────┐      ┌─────────────────────────┐                  │   │
│  │  │   PerformanceService    │◄────►│    VideoTestService     │                  │   │
│  │  │  - monitor_cpu()        │      │  - load_video()         │                  │   │
│  │  │  - benchmark_vad()      │      │  - extract_audio()      │                  │   │
│  │  │  - get_metrics()        │      │  - verify_subtitles()   │                  │   │
│  │  └─────────────────────────┘      └─────────────────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           PROCESSING ENGINES                                    │   │
│  ├─────────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                                 │   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────┐  │   │
│  │  │    VAD Engine           │  │    ASR Engine           │  │  Translation    │  │   │
│  │  │  ┌─────────────────┐    │  │  ┌─────────────────┐    │  │  Engine         │  │   │
│  │  │  │ Silero VAD      │    │  │  │ Whisper.cpp     │    │  │  ┌───────────┐  │  │   │
│  │  │  │ (PyTorch/ONNX)  │    │  │  │ (C++ bindings)  │    │  │  │ ArgosMT   │  │  │   │
│  │  │  └─────────────────┘    │  │  └─────────────────┘    │  │  └───────────┘  │  │   │
│  │  │  ┌─────────────────┐    │  │  ┌─────────────────┐    │  │  ┌───────────┐  │  │   │
│  │  │  │ WebRTC VAD      │    │  │  │ Faster-Whisper  │    │  │  │ OpusMT    │  │  │   │
│  │  │  │ (Google)        │    │  │  │ (Python)        │    │  │  │ (CT2)     │  │  │   │
│  │  │  └─────────────────┘    │  │  └─────────────────┘    │  │  └───────────┘  │  │   │
│  │  └─────────────────────────┘  └─────────────────────────┘  └─────────────────┘  │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           PLATFORM ABSTRACTION LAYER                            │   │
│  ├─────────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                                 │   │
│  │  ┌─────────────────────────┐              ┌─────────────────────────┐          │   │
│  │  │   Windows Platform      │              │   macOS Platform        │          │   │
│  │  │  ┌─────────────────┐    │              │  ┌─────────────────┐    │          │   │
│  │  │  │ WASAPI Capture  │    │              │  │ CoreAudio       │    │          │   │
│  │  │  │ (loopback)      │    │              │  │ (BlackHole)     │    │          │   │
│  │  │  └─────────────────┘    │              │  └─────────────────┘    │          │   │
│  │  │  ┌─────────────────┐    │              │  ┌─────────────────┐    │          │   │
│  │  │  │ DirectSound     │    │              │  │ AVFoundation    │    │          │   │
│  │  │  └─────────────────┘    │              │  └─────────────────┘    │          │   │
│  │  └─────────────────────────┘              └─────────────────────────┘          │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow & Workflow

### 4.1 Main Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      REAL-TIME PROCESSING PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   AUDIO INPUT                    PROCESSING                      OUTPUT                 │
│                                                                                         │
│   ┌─────────┐                                                                            │
│   │Microphone│                                                                           │
│   │  Input   │────┐                                                                      │
│   └─────────┘    │                                                                      │
│                  │                                                                      │
│   ┌─────────┐    │    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │ System  │────┼───▶│ Audio Buffer│───▶│   VAD       │───▶│Segmentation │            │
│   │ Audio   │    │    │  (Ring)     │    │ Detection   │    │   Engine    │            │
│   │ Capture │────┘    └─────────────┘    └─────────────┘    └──────┬──────┘            │
│   └─────────┘                                                      │                    │
│                                                                    ▼                    │
│                                                             ┌─────────────┐             │
│                                                             │  Speech     │             │
│                                                             │  Segment    │             │
│                                                             │  Queue      │             │
│                                                             └──────┬──────┘             │
│                                                                    │                    │
│                    ┌───────────────────────────────────────────────┘                    │
│                    │                                                                    │
│                    ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────────┐          │
│   │                      PROCESSING DECISION                                │          │
│   │  ┌─────────────────┐                    ┌─────────────────────────┐    │          │
│   │  │  Edge Mode?     │────YES────────────▶│  Local ASR (Whisper)    │    │          │
│   │  │  (Offline)      │                    │  - Load quantized model │    │          │
│   │  └─────────────────┘                    │  - Run on CPU/GPU       │    │          │
│   │           │                             │  - Transcribe segment   │    │          │
│   │           NO                            └─────────────────────────┘    │          │
│   │           │                                          │                  │          │
│   │           ▼                                          │                  │          │
│   │  ┌─────────────────┐                                 │                  │          │
│   │  │  Cloud Mode?    │────YES────────────▶│  Cloud ASR API          │    │          │
│   │  │  (Online)       │                    │  - REST/WebSocket call  │    │          │
│   │  └─────────────────┘                    │  - Send audio segment   │    │          │
│   │                                          └─────────────────────────┘    │          │
│   └─────────────────────────────────────────────────────────────────────────┘          │
│                                    │                                                    │
│                                    ▼                                                    │
│   ┌─────────────────────────────────────────────────────────────────────────┐          │
│   │                      TRANSLATION LAYER                                  │          │
│   │  ┌─────────────────┐                    ┌─────────────────────────┐    │          │
│   │  │  Source Text    │───────────────────▶│  Translation Engine     │    │          │
│   │  │  (ZH/EN/JA/FR)  │                    │  - Detect source lang   │    │          │
│   │  └─────────────────┘                    │  - Translate to target  │    │          │
│   │                                          │  - Post-process         │    │          │
│   │                                          └─────────────────────────┘    │          │
│   └─────────────────────────────────────────────────────────────────────────┘          │
│                                    │                                                    │
│                                    ▼                                                    │
│   ┌─────────────────────────────────────────────────────────────────────────┐          │
│   │                      OUTPUT DISPLAY                                     │          │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │          │
│   │  │   Original  │  │ Translated  │  │  Subtitle   │  │   Audio     │    │          │
│   │  │    Text     │  │    Text     │  │   Overlay   │  │ Waveform    │    │          │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │          │
│   └─────────────────────────────────────────────────────────────────────────┘          │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 State Machine Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION STATE MACHINE                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│                              ┌─────────────┐                                            │
│                              │    IDLE     │                                            │
│                              │  (Initial)  │                                            │
│                              └──────┬──────┘                                            │
│                                     │                                                   │
│                    ┌────────────────┼────────────────┐                                  │
│                    │                │                │                                  │
│                    ▼                ▼                ▼                                  │
│            ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                           │
│            │   CONFIG    │  │  TESTING    │  │  CAPTURING  │                           │
│            │  (Settings) │  │ (Audio Test)│  │  (Running)  │                           │
│            └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                           │
│                   │                │                │                                   │
│                   │                │                │                                   │
│                   ▼                ▼                ▼                                   │
│            ┌─────────────────────────────────────────────────┐                          │
│            │              PROCESSING STATES                  │                          │
│            ├─────────────────────────────────────────────────┤                          │
│            │                                                 │                          │
│            │   ┌─────────┐    ┌─────────┐    ┌─────────┐    │                          │
│            │   │  VAD_   │───▶│  ASR_   │───▶│TRANS_   │    │                          │
│            │   │ACTIVE   │    │PROCESS  │    │PROCESS  │    │                          │
│            │   └─────────┘    └─────────┘    └─────────┘    │                          │
│            │        │                              │         │                          │
│            │        └──────────────────────────────┘         │                          │
│            │                       │                         │                          │
│            │                       ▼                         │                          │
│            │               ┌─────────────┐                   │                          │
│            │               │  DISPLAY_   │                   │                          │
│            │               │  RESULTS    │                   │                          │
│            │               └─────────────┘                   │                          │
│            └─────────────────────────────────────────────────┘                          │
│                              │                                                          │
│                              ▼                                                          │
│                       ┌─────────────┐                                                   │
│                       │   PAUSED    │                                                   │
│                       │  (Standby)  │                                                   │
│                       └─────────────┘                                                   │
│                                                                                         │
│   STATE TRANSITIONS:                                                                    │
│   ─────────────────                                                                     │
│   IDLE → CONFIG:     User opens settings                                                │
│   IDLE → TESTING:    User runs audio test                                               │
│   IDLE → CAPTURING:  User starts capture                                                │
│   CAPTURING → VAD:   Voice detected                                                     │
│   VAD → ASR:         Segment complete                                                   │
│   ASR → TRANS:       Transcription ready                                                │
│   TRANS → DISPLAY:   Translation complete                                               │
│   ANY → PAUSED:      User pauses                                                        │
│   PAUSED → IDLE:     User stops                                                         │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Performance Monitoring Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      PERFORMANCE MONITORING WORKFLOW                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                         BENCHMARKING SYSTEM                                     │   │
│   ├─────────────────────────────────────────────────────────────────────────────────┤   │
│   │                                                                                 │   │
│   │   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌───────────┐  │   │
│   │   │   Timer     │─────▶│  CPU Usage  │─────▶│  Memory     │─────▶│  Metrics  │  │   │
│   │   │   Start     │      │  Monitor    │      │  Tracker    │      │  Store    │  │   │
│   │   └─────────────┘      └─────────────┘      └─────────────┘      └───────────┘  │   │
│   │                                                                                 │   │
│   │   MODULE-SPECIFIC BENCHMARKS:                                                 │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │  VAD Module:                                                            │   │   │
│   │   │  - Detection latency: < 50ms                                            │   │   │
│   │   │  - CPU usage: ~5-10% (single core)                                      │   │   │
│   │   │  - False positive rate: < 5%                                            │   │   │
│   │   │                                                                           │   │   │
│   │   │  Segmentation Module:                                                   │   │   │
│   │   │  - Processing time: < 20ms per segment                                  │   │   │
│   │   │  - Buffer overhead: < 100ms                                             │   │   │
│   │   │                                                                           │   │   │
│   │   │  ASR Module:                                                            │   │   │
│   │   │  - Transcription latency: 100-500ms (edge) / 200-800ms (cloud)          │   │   │
│   │   │  - CPU usage: 20-60% (depends on model)                                 │   │   │
│   │   │  - Memory usage: 500MB-2GB (model dependent)                            │   │   │
│   │   │                                                                           │   │   │
│   │   │  Translation Module:                                                    │   │   │
│   │   │  - Translation latency: 50-200ms                                        │   │   │
│   │   │  - CPU usage: 10-30%                                                    │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                                 │   │
│   │   VISUALIZATION:                                                              │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│   │   │  Real-time  │  │   CPU       │  │   Memory    │  │   Latency Graph     │  │   │
│   │   │  Dashboard  │  │   Gauge     │  │   Chart     │  │   (per module)      │  │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│   │                                                                                 │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Module Breakdown

### 5.1 Module Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           MODULE HIERARCHY                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  voice_translation_app/                                                                 │
│  │                                                                                      │
│  ├── gui/                           # Presentation Layer                                │
│  │   ├── __init__.py                                                                            │
│  │   ├── main_window.py            # Main application window                            │
│  │   ├── voice_visualizer.py       # Real-time waveform/spectrum display                │
│  │   ├── segment_timeline.py       # Voice segment visualization                        │
│  │   ├── translation_panel.py      # Original + translated text display                 │
│  │   ├── performance_panel.py      # CPU/Memory/Latency monitoring                      │
│  │   ├── settings_dialog.py        # Configuration UI                                   │
│  │   ├── audio_test_dialog.py      # Input source testing UI                           │
│  │   ├── subtitle_overlay.py       # Video subtitle overlay                             │
│  │   ├── theme/                     # Microsoft Edge-style theme                        │
│  │   │   ├── styles.qss             # Qt stylesheet                                     │
│  │   │   ├── colors.py              # Color palette definitions                         │
│  │   │   └── icons/                 # UI icons                                         │
│  │   └── widgets/                   # Reusable custom widgets                           │
│  │       ├── waveform_widget.py                                                        │
│  │       ├── meter_widget.py                                                           │
│  │       └── toggle_switch.py                                                          │
│  │                                                                                      │
│  ├── core/                          # Application Core                                  │
│  │   ├── __init__.py                                                                            │
│  │   ├── audio_manager.py          # Audio capture coordination                         │
│  │   ├── buffer_manager.py         # Ring buffer for audio chunks                      │
│  │   ├── config_manager.py         # Settings persistence                               │
│  │   ├── event_bus.py              # Inter-module communication                         │
│  │   ├── state_machine.py          # Application state management                       │
│  │   └── performance_profiler.py   # Benchmarking and metrics                           │
│  │                                                                                      │
│  ├── processing/                    # Processing Layer                                  │
│  │   ├── __init__.py                                                                            │
│  │   ├── vad/                       # Voice Activity Detection                          │
│  │   │   ├── __init__.py                                                                            │
│  │   │   ├── base_vad.py           # Abstract VAD interface                            │
│  │   │   ├── silero_vad.py         # Silero VAD implementation                         │
│  │   │   ├── webrtc_vad.py         # WebRTC VAD implementation                         │
│  │   │   └── vad_factory.py        # VAD engine selector                               │
│  │   │                                                                                  │
│  │   ├── segmentation/              # Audio Segmentation                                │
│  │   │   ├── __init__.py                                                                            │
│  │   │   ├── segmenter.py          # Main segmentation logic                           │
│  │   │   ├── energy_based.py        # Energy-based segmentation                        │
│  │   │   └── hybrid_segmenter.py    # VAD + energy hybrid                             │
│  │   │                                                                                  │
│  │   ├── asr/                       # Speech Recognition                                │
│  │   │   ├── __init__.py                                                                            │
│  │   │   ├── base_asr.py           # Abstract ASR interface                            │
│  │   │   ├── whisper_local.py       # Local Whisper implementation                     │
│  │   │   ├── whisper_cloud.py       # Cloud Whisper API                                │
│  │   │   └── asr_factory.py        # ASR engine selector                               │
│  │   │                                                                                  │
│  │   └── translation/               # Translation Engine                               │
│  │       ├── __init__.py                                                                            │
│  │       ├── base_translator.py     # Abstract translator interface                    │
│  │       ├── argos_translator.py    # ArgosMT local translation                       │
│  │       ├── opus_translator.py     # OpusMT/CT2 translation                          │
│  │       ├── cloud_translator.py    # Cloud translation APIs                          │
│  │       └── translator_factory.py  # Translator selector                              │
│  │                                                                                      │
│  ├── audio/                         # Audio I/O Layer                                   │
│  │   ├── __init__.py                                                                            │
│  │   ├── base_capture.py           # Abstract capture interface                        │
│  │   ├── microphone_capture.py     # Microphone input                                  │
│  │   ├── system_capture.py         # System audio capture                              │
│  │   ├── capture_factory.py        # Capture source selector                           │
│  │   ├── audio_tester.py           # Input testing utilities                           │
│  │   └── platform/                  # Platform-specific implementations                │
│  │       ├── windows/               # Windows WASAPI/DirectSound                       │
│  │       └── macos/                 # macOS CoreAudio/BlackHole                       │
│  │                                                                                      │
│  ├── video/                         # Video Testing                                     │
│  │   ├── __init__.py                                                                            │
│  │   ├── video_loader.py           # Video file handling                               │
│  │   ├── audio_extractor.py        # Extract audio from video                          │
│  │   └── subtitle_verifier.py      # Verify against reference subtitles                │
│  │                                                                                      │
│  ├── models/                        # Model Management                                  │
│  │   ├── __init__.py                                                                            │
│  │   ├── model_manager.py          # Download/cache models                             │
│  │   ├── whisper_models.py         # Whisper model configs                             │
│  │   └── translation_models.py     # Translation model configs                         │
│  │                                                                                      │
│  ├── utils/                         # Utilities                                         │
│  │   ├── __init__.py                                                                            │
│  │   ├── constants.py              # Application constants                             │
│  │   ├── logger.py                 # Logging setup                                     │
│  │   └── helpers.py                # Helper functions                                  │
│  │                                                                                      │
│  └── main.py                        # Application entry point                           │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Module Responsibilities

| Module | Responsibility | Key Functions |
|--------|---------------|---------------|
| **GUI Layer** | User interface, visualization, interaction | Render waveform, display translations, settings management |
| **Audio Manager** | Coordinate audio capture from multiple sources | Start/stop capture, switch sources, volume control |
| **Buffer Manager** | Manage audio data flow between components | Ring buffer, chunk management, overflow handling |
| **VAD Engine** | Detect voice activity in audio stream | Process audio chunks, return voice probability, trigger events |
| **Segmentation** | Split continuous audio into speech segments | Detect boundaries, manage segment queue, handle overlaps |
| **ASR Engine** | Convert speech to text | Load model, transcribe audio, return text with confidence |
| **Translation Engine** | Translate text between languages | Detect language, translate, post-process |
| **Performance Profiler** | Monitor system resources and latency | Track CPU, memory, per-module timing |
| **Config Manager** | Persist and load user settings | Save profiles, manage preferences |
| **Video Tester** | Test with video files and subtitles | Load video, extract audio, verify accuracy |

---

## 6. Interface Definitions

### 6.1 Core Interfaces

```python
# ============================================================
# AUDIO CAPTURE INTERFACE
# ============================================================

class IAudioCapture(ABC):
    """Abstract interface for audio capture sources"""
    
    @abstractmethod
    def initialize(self, sample_rate: int = 16000, channels: int = 1) -> bool:
        """Initialize the audio capture device"""
        pass
    
    @abstractmethod
    def start_capture(self, callback: Callable[[np.ndarray], None]) -> bool:
        """Start capturing audio with callback for each chunk"""
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """Stop audio capture"""
        pass
    
    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """Return device information"""
        pass
    
    @abstractmethod
    def test_input(self, duration_ms: int = 3000) -> AudioTestResult:
        """Test if input source is working"""
        pass

# ============================================================
# VAD INTERFACE
# ============================================================

class IVADEngine(ABC):
    """Abstract interface for Voice Activity Detection"""
    
    @abstractmethod
    def initialize(self, model_path: Optional[str] = None) -> bool:
        """Initialize VAD engine with optional model"""
        pass
    
    @abstractmethod
    def process(self, audio_chunk: np.ndarray) -> VADResult:
        """
        Process audio chunk and return voice activity detection result
        
        Returns:
            VADResult: Contains is_speech (bool), confidence (float), 
                      speech_probability (float)
        """
        pass
    
    @abstractmethod
    def set_threshold(self, threshold: float) -> None:
        """Set voice detection threshold (0.0 - 1.0)"""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset internal state"""
        pass

@dataclass
class VADResult:
    is_speech: bool
    confidence: float
    speech_probability: float
    timestamp: float

# ============================================================
# AUDIO SEGMENTATION INTERFACE
# ============================================================

class IAudioSegmenter(ABC):
    """Abstract interface for audio segmentation"""
    
    @abstractmethod
    def initialize(self, config: SegmentationConfig) -> bool:
        """Initialize segmenter with configuration"""
        pass
    
    @abstractmethod
    def feed_audio(self, audio_chunk: np.ndarray, 
                   vad_result: VADResult) -> Optional[AudioSegment]:
        """
        Feed audio chunk and VAD result, returns segment if complete
        """
        pass
    
    @abstractmethod
    def flush(self) -> Optional[AudioSegment]:
        """Force flush any pending audio as a segment"""
        pass
    
    @abstractmethod
    def get_pending_duration(self) -> float:
        """Get duration of pending audio in buffer"""
        pass

@dataclass
class AudioSegment:
    audio_data: np.ndarray
    start_time: float
    end_time: float
    duration: float
    sample_rate: int
    confidence: float

@dataclass
class SegmentationConfig:
    min_segment_duration: float = 1.0      # Minimum segment length (seconds)
    max_segment_duration: float = 30.0     # Maximum segment length (seconds)
    padding_before: float = 0.3            # Padding before speech (seconds)
    padding_after: float = 0.5             # Padding after speech (seconds)
    silence_threshold: float = 0.5         # Silence duration to split (seconds)

# ============================================================
# ASR INTERFACE
# ============================================================

class IASREngine(ABC):
    """Abstract interface for Speech Recognition"""
    
    @abstractmethod
    def initialize(self, model_config: ModelConfig) -> bool:
        """Initialize ASR engine with model configuration"""
        pass
    
    @abstractmethod
    def transcribe(self, audio_segment: AudioSegment) -> TranscriptionResult:
        """
        Transcribe audio segment to text
        
        Returns:
            TranscriptionResult: Contains text, confidence, language, segments
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes"""
        pass
    
    @abstractmethod
    def unload(self) -> None:
        """Unload model to free memory"""
        pass

@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    segments: List[TranscriptionSegment]
    processing_time: float

@dataclass
class TranscriptionSegment:
    start: float
    end: float
    text: str
    confidence: float

@dataclass
class ModelConfig:
    model_name: str
    model_path: Optional[str] = None
    device: str = "cpu"  # "cpu", "cuda", "mps" (Apple Silicon)
    compute_type: str = "int8"  # "int8", "float16", "float32"
    language: Optional[str] = None  # Auto-detect if None

# ============================================================
# TRANSLATION INTERFACE
# ============================================================

class ITranslator(ABC):
    """Abstract interface for Translation"""
    
    @abstractmethod
    def initialize(self, config: TranslationConfig) -> bool:
        """Initialize translator with configuration"""
        pass
    
    @abstractmethod
    def translate(self, text: str, source_lang: str, 
                  target_lang: str) -> TranslationResult:
        """
        Translate text from source to target language
        
        Returns:
            TranslationResult: Contains translated text, confidence
        """
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect the language of input text"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[LanguagePair]:
        """Return list of supported language pairs"""
        pass

@dataclass
class TranslationResult:
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    processing_time: float

@dataclass
class LanguagePair:
    source: str
    target: str
    name: str

@dataclass
class TranslationConfig:
    engine: str  # "argos", "opus", "cloud"
    model_path: Optional[str] = None
    beam_size: int = 5
    max_length: int = 512

# ============================================================
# PERFORMANCE MONITORING INTERFACE
# ============================================================

class IPerformanceMonitor(ABC):
    """Abstract interface for Performance Monitoring"""
    
    @abstractmethod
    def start_benchmark(self, module_name: str) -> BenchmarkContext:
        """Start benchmarking a module"""
        pass
    
    @abstractmethod
    def end_benchmark(self, context: BenchmarkContext) -> BenchmarkResult:
        """End benchmarking and return results"""
        pass
    
    @abstractmethod
    def get_cpu_usage(self) -> Dict[str, float]:
        """Get CPU usage by module"""
        pass
    
    @abstractmethod
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage by module (in MB)"""
        pass
    
    @abstractmethod
    def get_latency_report(self) -> Dict[str, LatencyStats]:
        """Get latency statistics by module"""
        pass

@dataclass
class BenchmarkContext:
    module_name: str
    start_time: float
    start_cpu: float
    start_memory: int

@dataclass
class BenchmarkResult:
    module_name: str
    duration_ms: float
    cpu_percent: float
    memory_mb: int
    timestamp: float

@dataclass
class LatencyStats:
    module_name: str
    min_ms: float
    max_ms: float
    avg_ms: float
    p95_ms: float
    p99_ms: float
```

### 6.2 Event Bus Interface

```python
# ============================================================
# EVENT BUS (Inter-module Communication)
# ============================================================

class EventBus:
    """Pub/Sub event bus for loose coupling between modules"""
    
    def subscribe(self, event_type: EventType, 
                  callback: Callable[[Event], None]) -> Subscription:
        """Subscribe to an event type"""
        pass
    
    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe from events"""
        pass
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers"""
        pass

class EventType(Enum):
    # Audio events
    AUDIO_CAPTURE_STARTED = auto()
    AUDIO_CAPTURE_STOPPED = auto()
    AUDIO_CHUNK_RECEIVED = auto()
    
    # VAD events
    VAD_VOICE_DETECTED = auto()
    VAD_VOICE_ENDED = auto()
    
    # Segmentation events
    SEGMENT_CREATED = auto()
    SEGMENT_QUEUE_UPDATED = auto()
    
    # ASR events
    ASR_TRANSCRIPTION_STARTED = auto()
    ASR_TRANSCRIPTION_COMPLETE = auto()
    ASR_TRANSCRIPTION_FAILED = auto()
    
    # Translation events
    TRANSLATION_STARTED = auto()
    TRANSLATION_COMPLETE = auto()
    
    # UI events
    UI_SETTINGS_CHANGED = auto()
    UI_THEME_CHANGED = auto()
    
    # Performance events
    PERFORMANCE_METRICS_UPDATED = auto()
    BENCHMARK_COMPLETE = auto()

@dataclass
class Event:
    event_type: EventType
    data: Dict[str, Any]
    timestamp: float
    source: str
```

---

## 7. Technology Stack

### 7.1 Recommended Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           TECHNOLOGY STACK                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           PROGRAMMING LANGUAGE                                  │   │
│  │                                                                                 │   │
│  │   Primary: Python 3.10+ (Cross-platform, rich ML ecosystem)                     │   │
│  │   Critical Paths: C++ extensions (Whisper.cpp, performance-critical code)       │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           GUI FRAMEWORK                                         │   │
│  │                                                                                 │   │
│  │   Framework: PyQt6 / PySide6 (Qt 6.4+)                                          │   │
│  │   Styling: QSS (Qt Stylesheets) - Microsoft Edge theme                          │   │
│  │   Visualization: PyQtGraph (real-time waveform), Matplotlib (statistics)        │   │
│  │                                                                                 │   │
│  │   Alternative: Dear PyGui (lighter, but less mature)                            │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           AUDIO PROCESSING                                      │   │
│  │                                                                                 │   │
│  │   Audio I/O:                                                                    │   │
│  │   - sounddevice (PortAudio wrapper) - Cross-platform                            │   │
│  │   - PyAudio - Alternative, well-established                                     │   │
│  │                                                                                 │   │
│  │   System Audio Capture:                                                         │   │
│  │   - Windows: WASAPI loopback (via sounddevice)                                  │   │
│  │   - macOS: BlackHole virtual audio driver + CoreAudio                           │   │
│  │                                                                                 │   │
│  │   Audio Processing:                                                             │   │
│  │   - librosa - Audio analysis, feature extraction                                │   │
│  │   - numpy - Numerical operations on audio arrays                                │   │
│  │   - scipy.signal - Signal processing utilities                                  │   │
│  │   - soundfile - Audio file I/O                                                  │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           VOICE ACTIVITY DETECTION                              │   │
│  │                                                                                 │   │
│  │   Primary: Silero VAD (PyTorch-based, high accuracy)                            │   │
│  │   Alternative: WebRTC VAD (Google, lightweight, fast)                           │   │
│  │   ONNX Runtime: For faster inference without PyTorch dependency                 │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           SPEECH RECOGNITION (ASR)                              │   │
│  │                                                                                 │   │
│  │   Local Edge (Recommended):                                                     │   │
│  │   - whisper.cpp (C++ port) + Python bindings                                    │   │
│  │     * Optimized for Apple Silicon (M1/M2) via Metal/GPU                         │   │
│  │     * Quantized models (tiny, base, small) for different accuracy/speed         │   │
│  │   - faster-whisper (CTranslate2 backend)                                        │   │
│  │     * Faster than original Whisper                                              │   │
│  │     * Supports GPU acceleration                                                 │   │
│  │                                                                                 │   │
│  │   Cloud (Optional Fallback):                                                    │   │
│  │   - OpenAI Whisper API                                                          │   │
│  │   - Google Cloud Speech-to-Text                                                 │   │
│  │   - Azure Speech Services                                                       │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           TRANSLATION ENGINE                                    │   │
│  │                                                                                 │   │
│  │   Local Edge (Recommended):                                                     │   │
│  │   - Argos Translate (Open-source, offline)                                      │   │
│  │     * Supports ZH, EN, JA, FR                                                   │   │
│  │     * Lightweight models                                                        │   │
│  │   - Opus-MT + CTranslate2 (Faster inference)                                    │   │
│  │     * Hugging Face models                                                       │   │
│  │     * Better quality for some language pairs                                    │   │
│  │                                                                                 │   │
│  │   Cloud (Optional):                                                             │   │
│  │   - LibreTranslate API (self-hosted option)                                     │   │
│  │   - Google Cloud Translation                                                    │   │
│  │   - DeepL API (high quality)                                                    │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           MODEL MANAGEMENT                                      │   │
│  │                                                                                 │   │
│  │   Model Download: Hugging Face Hub, direct URLs                                 │   │
│  │   Model Cache: Local directory (~/.voice_translate/models/)                     │   │
│  │   Model Formats: ONNX, GGML (whisper.cpp), CTranslate2                          │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           PERFORMANCE MONITORING                                │   │
│  │                                                                                 │   │
│  │   CPU/Memory: psutil (cross-platform system monitoring)                         │   │
│  │   Timing: time.perf_counter() for high-precision measurements                   │   │
│  │   Profiling: cProfile for detailed analysis, line_profiler for hotspots         │   │
│  │   Visualization: Real-time plots with PyQtGraph                                 │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           VIDEO TESTING                                         │   │
│  │                                                                                 │   │
│  │   Video Processing: ffmpeg-python, opencv-python                                │   │
│  │   Audio Extraction: ffmpeg, pydub                                               │   │
│  │   Subtitle Parsing: pysrt, webvtt-py                                            │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           BUILD & DISTRIBUTION                                  │   │
│  │                                                                                 │   │
│  │   Packaging: PyInstaller (Windows), py2app (macOS)                              │   │
│  │   Dependency Management: poetry or pip + requirements.txt                       │   │
│  │   Virtual Environment: venv, conda                                              │   │
│  │                                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Technology Comparison Matrix

| Component | Option 1 (Recommended) | Option 2 | Option 3 |
|-----------|----------------------|----------|----------|
| GUI | PyQt6 | PySide6 | Dear PyGui |
| Audio I/O | sounddevice | PyAudio | soundcard |
| VAD | Silero VAD | WebRTC VAD | Energy-based |
| ASR (Local) | whisper.cpp | faster-whisper | whisper-openai |
| Translation | ArgosMT | Opus-MT | MarianMT |
| Plotting | PyQtGraph | Matplotlib | Plotly |

### 7.3 Model Selection Guide

| Model | Size | Languages | Speed | Quality | Use Case |
|-------|------|-----------|-------|---------|----------|
| Whisper Tiny | 39 MB | Multilingual | Very Fast | Good | Real-time, low latency |
| Whisper Base | 74 MB | Multilingual | Fast | Better | Balanced performance |
| Whisper Small | 244 MB | Multilingual | Medium | Best | Higher accuracy needed |
| Whisper Medium | 769 MB | Multilingual | Slow | Excellent | Offline, accuracy priority |

---

## 8. Design Document Structure

### 8.1 Complete Documentation Tree

```
docs/
├── README.md                          # Project overview and quick start
├── architecture/
│   ├── system_overview.md             # High-level system description
│   ├── block_diagrams.md              # All system block diagrams
│   ├── component_architecture.md      # Component relationships
│   ├── data_flow.md                   # Data flow documentation
│   └── deployment.md                  # Deployment configurations
│
├── design/
│   ├── gui_design.md                  # GUI mockups and design specs
│   ├── theme_specification.md         # Microsoft Edge theme details
│   ├── color_palette.md               # Color definitions
│   └── interaction_design.md          # User interaction flows
│
├── api/
│   ├── interfaces.md                  # All interface definitions
│   ├── events.md                      # Event bus documentation
│   ├── audio_capture_api.md           # Audio capture interface
│   ├── vad_api.md                     # VAD interface
│   ├── asr_api.md                     # ASR interface
│   └── translation_api.md             # Translation interface
│
├── modules/
│   ├── gui_module.md                  # GUI module documentation
│   ├── audio_module.md                # Audio module documentation
│   ├── vad_module.md                  # VAD module documentation
│   ├── segmentation_module.md         # Segmentation module documentation
│   ├── asr_module.md                  # ASR module documentation
│   ├── translation_module.md          # Translation module documentation
│   └── performance_module.md          # Performance monitoring docs
│
├── technology/
│   ├── stack_overview.md              # Technology stack summary
│   ├── dependencies.md                # All dependencies listed
│   ├── model_guide.md                 # Model selection guide
│   └── platform_notes.md              # Windows/macOS specific notes
│
├── development/
│   ├── setup.md                       # Development environment setup
│   ├── building.md                    # Build instructions
│   ├── testing.md                     # Testing procedures
│   └── profiling.md                   # Performance profiling guide
│
├── user/
│   ├── user_manual.md                 # End-user documentation
│   ├── installation.md                # Installation guide
│   ├── configuration.md               # Configuration options
│   └── troubleshooting.md             # Common issues and solutions
│
└── diagrams/
    ├── system_block_diagram.png       # Visual system diagram
    ├── component_diagram.png          # Component architecture
    ├── data_flow_diagram.png          # Data flow visualization
    ├── state_machine.png              # State machine diagram
    └── sequence_diagrams/             # Sequence diagrams for key flows
        ├── capture_to_display.md
        ├── settings_change.md
        └── video_test_flow.md
```

### 8.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| GUI Framework | PyQt6 | Mature, cross-platform, native look, rich widgets |
| VAD Engine | Silero VAD | High accuracy, ONNX support, actively maintained |
| ASR Engine (Edge) | whisper.cpp | Optimized for Apple Silicon, quantized models, fast |
| Translation (Edge) | ArgosMT | Fully offline, open-source, supports required languages |
| Audio Capture | sounddevice | Cross-platform, simple API, low latency |
| System Audio (macOS) | BlackHole | Free, reliable, well-documented |
| System Audio (Windows) | WASAPI Loopback | Native, no additional drivers |
| Performance Monitoring | psutil + custom | Cross-platform, lightweight, detailed |

---

## Appendix A: Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| End-to-end Latency | < 1 second | From speech to translation display |
| VAD Latency | < 50ms | Voice detection response time |
| ASR Latency (Edge) | 100-500ms | Depends on model size |
| Translation Latency | 50-200ms | Local translation |
| CPU Usage (VAD) | < 10% | Single core |
| CPU Usage (ASR) | 20-60% | Depends on model and hardware |
| Memory Usage | < 2GB | With medium-sized models |
| Frame Rate (GUI) | 30 FPS | Smooth waveform visualization |

## Appendix B: Language Support Matrix

| Source \ Target | English | Chinese | Japanese | French |
|-----------------|---------|---------|----------|--------|
| English | - | ✓ | ✓ | ✓ |
| Chinese | ✓ | - | ✓ | ✓ |
| Japanese | ✓ | ✓ | - | ✓ |
| French | ✓ | ✓ | ✓ | - |

## Appendix C: Platform-Specific Notes

### Windows
- Use WASAPI loopback for system audio capture
- PyInstaller for executable packaging
- Consider Windows-specific audio APIs for lower latency

### macOS (Apple Silicon M1 Pro)
- Use BlackHole for system audio capture
- Leverage Metal Performance Shaders for Whisper acceleration
- Universal2 binary for Intel + Apple Silicon support
- Code signing required for distribution

---

*Document Version: 1.0*  
*Last Updated: 2024*  
*Author: System Architecture Team*
