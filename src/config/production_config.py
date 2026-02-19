"""
Production Configuration Management - Phase 2.2

Provides environment-specific configuration with validation,
secret management, and runtime overrides.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ASRConfig:
    """ASR-specific configuration."""
    model_size: str = "base"
    compute_type: str = "int8"
    beam_size: int = 5
    
    # Hardware backend selection
    backend: str = "auto"  # auto, openvino, coreml, fallback
    
    # Draft mode settings
    draft_compute_type: str = "int8"
    draft_beam_size: int = 1
    draft_interval_ms: int = 2000
    
    # Performance tuning
    max_concurrent_workers: int = 2
    batch_size: int = 1


@dataclass
class TranslationConfig:
    """Translation-specific configuration."""
    # Translation models by size
    model_tier: str = "fast"  # fast, balanced, accurate
    
    # Language-specific settings
    enforce_sov_punctuation: bool = True
    sov_languages: List[str] = field(default_factory=lambda: ['ja', 'ko', 'de', 'tr', 'hi', 'fa'])
    
    # Semantic gating
    require_verbs_svo: bool = True
    min_draft_length: int = 5
    
    # Stability
    stability_threshold: float = 0.85
    max_history_segments: int = 5


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    # Audio settings
    sample_rate: int = 16000
    chunk_duration_ms: int = 100
    max_segment_duration_ms: int = 12000  # 12s for documentary/news long sentences
    silence_threshold_ms: int = 600
    
    # Adaptive controller
    enable_adaptive_draft: bool = True
    min_draft_interval_ms: int = 2000
    max_queue_depth: int = 3
    pause_skip_threshold_ms: int = 500
    
    # Performance targets
    target_ttft_ms: int = 2000
    target_meaning_latency_ms: int = 2000
    target_ear_voice_lag_ms: int = 500


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    # Metrics collection
    enable_metrics: bool = True
    metrics_export_interval_sec: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json, text
    log_destination: str = "stdout"  # stdout, file, both
    log_file_path: Optional[str] = None
    
    # Health checks
    enable_health_endpoint: bool = True
    health_check_port: int = 8080
    
    # Alerting
    alert_on_queue_overflow: bool = True
    alert_on_high_latency: bool = True
    latency_alert_threshold_ms: int = 3000
    
    # Tracing
    enable_tracing: bool = False
    tracing_endpoint: Optional[str] = None


@dataclass
class SecurityConfig:
    """Security and privacy configuration."""
    # API keys (loaded from environment)
    translation_api_key: Optional[str] = None
    
    # Data retention
    enable_audio_logging: bool = False
    audio_retention_hours: int = 24
    
    # Privacy
    local_only: bool = False  # Disable cloud services
    encrypt_temp_files: bool = True
    
    # Rate limiting
    rate_limit_requests_per_minute: int = 100


@dataclass
class UIConfig:
    """UI configuration."""
    # Display
    show_stability_indicators: bool = True
    show_latency_metrics: bool = True
    theme: str = "system"  # light, dark, system
    
    # Diff visualization
    enable_diff_highlighting: bool = True
    transition_animation_ms: int = 200
    
    # Debug
    show_segment_uuids: bool = False
    show_queue_depth: bool = False


@dataclass
class ProductionConfig:
    """Complete production configuration."""
    
    environment: Environment = Environment.DEVELOPMENT
    version: str = "1.0.0"
    
    # Component configs
    asr: ASRConfig = field(default_factory=ASRConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding secrets)."""
        data = asdict(self)
        data['environment'] = self.environment.value
        # Redact secrets
        if data.get('security', {}).get('translation_api_key'):
            data['security']['translation_api_key'] = '***REDACTED***'
        return data
    
    def save(self, path: str):
        """Save configuration to JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Configuration saved to {path}")
    
    @classmethod
    def from_json(cls, path: str) -> 'ProductionConfig':
        """Load configuration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls._from_dict(data)
    
    @classmethod
    def from_env(cls) -> 'ProductionConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Environment
        env_str = os.getenv('VOICETRANSLATE_ENV', 'development').upper()
        config.environment = Environment[env_str]
        
        # ASR config
        config.asr.model_size = os.getenv('VOICETRANSLATE_ASR_MODEL', config.asr.model_size)
        config.asr.backend = os.getenv('VOICETRANSLATE_ASR_BACKEND', config.asr.backend)
        config.asr.compute_type = os.getenv('VOICETRANSLATE_ASR_COMPUTE_TYPE', config.asr.compute_type)
        
        # Translation config
        config.translation.model_tier = os.getenv('VOICETRANSLATE_TRANSLATION_TIER', config.translation.model_tier)
        
        # Pipeline config
        config.pipeline.target_ttft_ms = int(os.getenv('VOICETRANSLATE_TARGET_TTFT', config.pipeline.target_ttft_ms))
        
        # Monitoring config
        config.monitoring.log_level = os.getenv('VOICETRANSLATE_LOG_LEVEL', config.monitoring.log_level)
        config.monitoring.enable_metrics = os.getenv('VOICETRANSLATE_ENABLE_METRICS', 'true').lower() == 'true'
        
        # Security config
        config.security.translation_api_key = os.getenv('TRANSLATION_API_KEY')
        
        return config
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'ProductionConfig':
        """Create config from dictionary."""
        config = cls()
        
        if 'environment' in data:
            config.environment = Environment(data['environment'])
        if 'version' in data:
            config.version = data['version']
        if 'asr' in data:
            config.asr = ASRConfig(**data['asr'])
        if 'translation' in data:
            config.translation = TranslationConfig(**data['translation'])
        if 'pipeline' in data:
            config.pipeline = PipelineConfig(**data['pipeline'])
        if 'monitoring' in data:
            config.monitoring = MonitoringConfig(**data['monitoring'])
        if 'security' in data:
            config.security = SecurityConfig(**data['security'])
        if 'ui' in data:
            config.ui = UIConfig(**data['ui'])
            
        return config
    
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # ASR validation
        valid_compute_types = ['int8', 'int8_float16', 'float16', 'float32']
        if self.asr.compute_type not in valid_compute_types:
            errors.append(f"Invalid compute_type: {self.asr.compute_type}")
        
        valid_backends = ['auto', 'openvino', 'coreml', 'fallback']
        if self.asr.backend not in valid_backends:
            errors.append(f"Invalid backend: {self.asr.backend}")
        
        # Pipeline validation
        if self.pipeline.target_ttft_ms < 100:
            errors.append(f"target_ttft_ms too low: {self.pipeline.target_ttft_ms}")
        if self.pipeline.max_segment_duration_ms < 1000:
            errors.append(f"max_segment_duration_ms too low: {self.pipeline.max_segment_duration_ms}")
        
        # Security validation
        if self.environment == Environment.PRODUCTION:
            if not self.security.translation_api_key and not self.security.local_only:
                errors.append("Translation API key required for production")
        
        return errors


# Global config instance
_global_config: Optional[ProductionConfig] = None


def get_config() -> ProductionConfig:
    """
    Get the global configuration instance.
    
    Loads from (in order of precedence):
    1. Environment variables
    2. Config file (if exists)
    3. Defaults
    """
    global _global_config
    
    if _global_config is None:
        # Start with defaults
        config = ProductionConfig()
        
        # Override with config file if exists
        config_paths = [
            Path.cwd() / "config" / "production.json",
            Path.home() / ".voicetranslate" / "config.json",
            Path("/etc/voicetranslate/config.json"),
        ]
        
        for path in config_paths:
            if path.exists():
                logger.info(f"Loading config from {path}")
                config = ProductionConfig.from_json(str(path))
                break
        
        # Override with environment variables
        env_config = ProductionConfig.from_env()
        config.environment = env_config.environment
        config.asr.backend = env_config.asr.backend
        config.monitoring.log_level = env_config.monitoring.log_level
        config.security.translation_api_key = env_config.security.translation_api_key
        
        # Validate
        errors = config.validate()
        if errors:
            logger.error("Configuration validation errors:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Invalid configuration")
        
        _global_config = config
        logger.info(f"Configuration loaded for environment: {config.environment.value}")
    
    return _global_config


def reload_config():
    """Reload configuration (useful for testing)."""
    global _global_config
    _global_config = None
    return get_config()


def create_default_configs():
    """Create default configuration files for all environments."""
    base_path = Path.cwd() / "config"
    base_path.mkdir(exist_ok=True)
    
    configs = {
        'development.json': ProductionConfig(environment=Environment.DEVELOPMENT),
        'staging.json': ProductionConfig(environment=Environment.STAGING),
        'production.json': ProductionConfig(environment=Environment.PRODUCTION),
    }
    
    for filename, config in configs.items():
        # Adjust settings for each environment
        if filename == 'production.json':
            config.monitoring.log_level = 'WARNING'
            config.monitoring.enable_metrics = True
            config.security.enable_audio_logging = False
            config.ui.show_latency_metrics = False
        elif filename == 'staging.json':
            config.monitoring.log_level = 'INFO'
            config.monitoring.enable_metrics = True
            config.ui.show_latency_metrics = True
        
        config.save(base_path / filename)
    
    logger.info(f"Created default configs in {base_path}")
