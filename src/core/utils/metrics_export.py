"""
Metrics Export System - Phase 2.2

Exports streaming metrics to various backends:
- Prometheus (for Grafana dashboards)
- InfluxDB (for time-series analysis)
- JSON file (for debugging)
- StatsD (for Datadog compatibility)

Usage:
    from src.core.utils.metrics_export import MetricsExporter
    
    exporter = MetricsExporter()
    exporter.export_metrics(metrics_snapshot)
"""

import json
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MetricsSnapshot:
    """Snapshot of streaming metrics."""
    timestamp: float
    
    # Latency metrics (ms)
    ttft_p50: float
    ttft_p99: float
    meaning_latency_p50: float
    meaning_latency_p99: float
    ear_voice_lag_ms: float
    
    # Quality metrics
    draft_stability: float
    segments_completed: int
    segments_dropped: int
    
    # Resource metrics
    cpu_percent: float
    memory_mb: float
    gpu_utilization: Optional[float] = None
    
    # Queue metrics
    asr_queue_depth: int
    translation_queue_depth: int
    
    # Custom metrics
    custom: Dict[str, float] = None
    
    def __post_init__(self):
        if self.custom is None:
            self.custom = {}


class MetricsExporter:
    """
    Multi-backend metrics exporter.
    
    Supports:
    - Prometheus text format
    - InfluxDB line protocol
    - JSON file export
    - StatsD UDP
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._exporters: List[Callable[[MetricsSnapshot], None]] = []
        self._lock = threading.Lock()
        
        # Initialize enabled exporters
        self._init_exporters()
    
    def _init_exporters(self):
        """Initialize configured exporters."""
        if self.config.get('prometheus', {}).get('enabled', False):
            self._exporters.append(self._export_prometheus)
            
        if self.config.get('influxdb', {}).get('enabled', False):
            self._exporters.append(self._export_influxdb)
            
        if self.config.get('json_file', {}).get('enabled', True):
            self._exporters.append(self._export_json)
            
        if self.config.get('statsd', {}).get('enabled', False):
            self._exporters.append(self._export_statsd)
    
    def export_metrics(self, snapshot: MetricsSnapshot):
        """Export metrics to all configured backends."""
        for exporter in self._exporters:
            try:
                exporter(snapshot)
            except Exception as e:
                logger.error(f"Metrics export failed: {e}")
    
    def _export_prometheus(self, snapshot: MetricsSnapshot):
        """Export in Prometheus text format."""
        config = self.config.get('prometheus', {})
        output_path = config.get('path', '/tmp/metrics.prom')
        
        lines = [
            "# HELP voicetranslate_ttft_ms Time to first token latency",
            "# TYPE voicetranslate_ttft_ms gauge",
            f"voicetranslate_ttft_ms{{quantile=\"p50\"}} {snapshot.ttft_p50}",
            f"voicetranslate_ttft_ms{{quantile=\"p99\"}} {snapshot.ttft_p99}",
            "",
            "# HELP voicetranslate_meaning_latency_ms Time to meaning latency",
            "# TYPE voicetranslate_meaning_latency_ms gauge",
            f"voicetranslate_meaning_latency_ms{{quantile=\"p50\"}} {snapshot.meaning_latency_p50}",
            f"voicetranslate_meaning_latency_ms{{quantile=\"p99\"}} {snapshot.meaning_latency_p99}",
            "",
            "# HELP voicetranslate_ear_voice_lag_ms Ear-to-voice lag",
            "# TYPE voicetranslate_ear_voice_lag_ms gauge",
            f"voicetranslate_ear_voice_lag_ms {snapshot.ear_voice_lag_ms}",
            "",
            "# HELP voicetranslate_draft_stability Draft stability score",
            "# TYPE voicetranslate_draft_stability gauge",
            f"voicetranslate_draft_stability {snapshot.draft_stability}",
            "",
            "# HELP voicetranslate_segments_completed Total segments completed",
            "# TYPE voicetranslate_segments_completed counter",
            f"voicetranslate_segments_completed {snapshot.segments_completed}",
            "",
            "# HELP voicetranslate_segments_dropped Total segments dropped",
            "# TYPE voicetranslate_segments_dropped counter",
            f"voicetranslate_segments_dropped {snapshot.segments_dropped}",
            "",
            "# HELP voicetranslate_cpu_percent CPU utilization",
            "# TYPE voicetranslate_cpu_percent gauge",
            f"voicetranslate_cpu_percent {snapshot.cpu_percent}",
            "",
            "# HELP voicetranslate_memory_mb Memory usage in MB",
            "# TYPE voicetranslate_memory_mb gauge",
            f"voicetranslate_memory_mb {snapshot.memory_mb}",
            "",
            "# HELP voicetranslate_queue_depth Queue depth",
            "# TYPE voicetranslate_queue_depth gauge",
            f"voicetranslate_queue_depth{{queue=\"asr\"}} {snapshot.asr_queue_depth}",
            f"voicetranslate_queue_depth{{queue=\"translation\"}} {snapshot.translation_queue_depth}",
        ]
        
        if snapshot.gpu_utilization is not None:
            lines.extend([
                "",
                "# HELP voicetranslate_gpu_utilization GPU utilization percent",
                "# TYPE voicetranslate_gpu_utilization gauge",
                f"voicetranslate_gpu_utilization {snapshot.gpu_utilization}",
            ])
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
    
    def _export_influxdb(self, snapshot: MetricsSnapshot):
        """Export in InfluxDB line protocol."""
        config = self.config.get('influxdb', {})
        
        # Build line protocol
        timestamp_ns = int(snapshot.timestamp * 1e9)
        
        lines = [
            f"voicetranslate_latency,metric=ttft p50={snapshot.ttft_p50},p99={snapshot.ttft_p99} {timestamp_ns}",
            f"voicetranslate_latency,metric=meaning p50={snapshot.meaning_latency_p50},p99={snapshot.meaning_latency_p99} {timestamp_ns}",
            f"voicetranslate_quality stability={snapshot.draft_stability},segments_completed={snapshot.segments_completed}i,segments_dropped={snapshot.segments_dropped}i {timestamp_ns}",
            f"voicetranslate_resources cpu={snapshot.cpu_percent},memory={snapshot.memory_mb} {timestamp_ns}",
            f"voicetranslate_queue asr={snapshot.asr_queue_depth}i,translation={snapshot.translation_queue_depth}i {timestamp_ns}",
        ]
        
        # Send via HTTP or UDP
        if config.get('url'):
            import urllib.request
            data = '\n'.join(lines).encode()
            req = urllib.request.Request(
                config['url'],
                data=data,
                headers={'Content-Type': 'text/plain'}
            )
            urllib.request.urlopen(req, timeout=5)
        
        # Also write to file for testing
        output_path = config.get('path', '/tmp/metrics.influx')
        with open(output_path, 'a') as f:
            f.write('\n'.join(lines) + '\n')
    
    def _export_json(self, snapshot: MetricsSnapshot):
        """Export to JSON file."""
        config = self.config.get('json_file', {})
        output_path = config.get('path', '/tmp/metrics.json')
        
        # Read existing or create new
        data = []
        if Path(output_path).exists():
            with open(output_path) as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        
        # Add new snapshot
        data.append({
            'timestamp': snapshot.timestamp,
            'ttft_p50': snapshot.ttft_p50,
            'ttft_p99': snapshot.ttft_p99,
            'meaning_latency_p50': snapshot.meaning_latency_p50,
            'meaning_latency_p99': snapshot.meaning_latency_p99,
            'ear_voice_lag_ms': snapshot.ear_voice_lag_ms,
            'draft_stability': snapshot.draft_stability,
            'segments_completed': snapshot.segments_completed,
            'segments_dropped': snapshot.segments_dropped,
            'cpu_percent': snapshot.cpu_percent,
            'memory_mb': snapshot.memory_mb,
            'gpu_utilization': snapshot.gpu_utilization,
            'asr_queue_depth': snapshot.asr_queue_depth,
            'translation_queue_depth': snapshot.translation_queue_depth,
            'custom': snapshot.custom
        })
        
        # Keep only last N entries
        max_entries = config.get('max_entries', 1000)
        data = data[-max_entries:]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _export_statsd(self, snapshot: MetricsSnapshot):
        """Export via StatsD UDP."""
        config = self.config.get('statsd', {})
        host = config.get('host', 'localhost')
        port = config.get('port', 8125)
        prefix = config.get('prefix', 'voicetranslate')
        
        import socket
        
        metrics = [
            f"{prefix}.latency.ttft.p50:{snapshot.ttft_p50}|g",
            f"{prefix}.latency.ttft.p99:{snapshot.ttft_p99}|g",
            f"{prefix}.latency.meaning.p50:{snapshot.meaning_latency_p50}|g",
            f"{prefix}.latency.meaning.p99:{snapshot.meaning_latency_p99}|g",
            f"{prefix}.quality.stability:{snapshot.draft_stability}|g",
            f"{prefix}.segments.completed:{snapshot.segments_completed}|c",
            f"{prefix}.segments.dropped:{snapshot.segments_dropped}|c",
            f"{prefix}.resources.cpu:{snapshot.cpu_percent}|g",
            f"{prefix}.resources.memory:{snapshot.memory_mb}|g",
        ]
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for metric in metrics:
            sock.sendto(metric.encode(), (host, port))
        sock.close()


class MetricsCollector:
    """
    Collects and aggregates metrics over time windows.
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._ttft_values: List[float] = []
        self._meaning_values: List[float] = []
        self._stability_values: List[float] = []
        self._lock = threading.Lock()
        
        self._segments_completed = 0
        self._segments_dropped = 0
    
    def record_ttft(self, value_ms: float):
        """Record a TTFT measurement."""
        with self._lock:
            self._ttft_values.append(value_ms)
            if len(self._ttft_values) > self.window_size:
                self._ttft_values.pop(0)
    
    def record_meaning_latency(self, value_ms: float):
        """Record a meaning latency measurement."""
        with self._lock:
            self._meaning_values.append(value_ms)
            if len(self._meaning_values) > self.window_size:
                self._meaning_values.pop(0)
    
    def record_stability(self, value: float):
        """Record a draft stability score."""
        with self._lock:
            self._stability_values.append(value)
            if len(self._stability_values) > self.window_size:
                self._stability_values.pop(0)
    
    def increment_completed(self):
        """Increment completed segments counter."""
        with self._lock:
            self._segments_completed += 1
    
    def increment_dropped(self):
        """Increment dropped segments counter."""
        with self._lock:
            self._segments_dropped += 1
    
    def get_snapshot(self) -> MetricsSnapshot:
        """Get current metrics snapshot."""
        import psutil
        
        with self._lock:
            # Calculate percentiles
            ttft_p50 = self._percentile(self._ttft_values, 50) if self._ttft_values else 0
            ttft_p99 = self._percentile(self._ttft_values, 99) if self._ttft_values else 0
            meaning_p50 = self._percentile(self._meaning_values, 50) if self._meaning_values else 0
            meaning_p99 = self._percentile(self._meaning_values, 99) if self._meaning_values else 0
            stability = sum(self._stability_values) / len(self._stability_values) if self._stability_values else 0
            
            # Get system resources
            cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory().used / (1024 * 1024)
            
            return MetricsSnapshot(
                timestamp=time.time(),
                ttft_p50=ttft_p50,
                ttft_p99=ttft_p99,
                meaning_latency_p50=meaning_p50,
                meaning_latency_p99=meaning_p99,
                ear_voice_lag_ms=0,  # TODO: Calculate from segments
                draft_stability=stability,
                segments_completed=self._segments_completed,
                segments_dropped=self._segments_dropped,
                cpu_percent=cpu,
                memory_mb=memory,
                asr_queue_depth=0,  # TODO: Get from queue monitor
                translation_queue_depth=0
            )
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        if f == c:
            return sorted_values[f]
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


# Convenience function for quick export
def export_simple_metrics(
    ttft_ms: float,
    meaning_latency_ms: float,
    output_file: str = '/tmp/metrics.json'
):
    """Export simple metrics to JSON file."""
    snapshot = MetricsSnapshot(
        timestamp=time.time(),
        ttft_p50=ttft_ms,
        ttft_p99=ttft_ms,
        meaning_latency_p50=meaning_latency_ms,
        meaning_latency_p99=meaning_latency_ms,
        ear_voice_lag_ms=0,
        draft_stability=0.9,
        segments_completed=1,
        segments_dropped=0,
        cpu_percent=0,
        memory_mb=0
    )
    
    exporter = MetricsExporter(config={
        'json_file': {'enabled': True, 'path': output_file}
    })
    exporter.export_metrics(snapshot)
