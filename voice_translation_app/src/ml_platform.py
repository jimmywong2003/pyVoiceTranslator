"""
Cross-Platform ML Optimization Layer
Supports: Apple Silicon (MPS), Windows (CUDA/DirectML), CPU fallback
"""

import platform
import sys
import os
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import warnings

logger = logging.getLogger(__name__)


@dataclass
class MLPlatformConfig:
    """ML platform configuration"""
    device: str = "auto"  # auto, cpu, cuda, mps, directml
    precision: str = "fp32"  # fp32, fp16, int8
    batch_size: int = 1
    num_threads: int = 0  # 0 = auto
    enable_optimization: bool = True


class PlatformOptimizer:
    """Base class for platform-specific ML optimizations"""
    
    def __init__(self, config: MLPlatformConfig):
        self.config = config
        self.device = None
        self.device_name = "cpu"
        self.is_available = False
    
    def setup(self) -> bool:
        """Setup the platform optimization"""
        raise NotImplementedError
    
    def optimize_model(self, model: Any) -> Any:
        """Apply platform-specific optimizations to model"""
        return model
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        return {
            'device': self.device_name,
            'available': self.is_available,
            'config': self.config
        }


# =============================================================================
# Apple Silicon Optimizations (MPS - Metal Performance Shaders)
# =============================================================================

class AppleSiliconOptimizer(PlatformOptimizer):
    """Apple Silicon M1/M2/M3 optimizations using MPS"""
    
    def __init__(self, config: MLPlatformConfig):
        super().__init__(config)
        self.torch = None
        self.mps_available = False
    
    def setup(self) -> bool:
        """Setup MPS backend for Apple Silicon"""
        try:
            import torch
            self.torch = torch
            
            # Check MPS availability
            self.mps_available = torch.backends.mps.is_available()
            mps_built = torch.backends.mps.is_built()
            
            logger.info(f"PyTorch MPS built: {mps_built}")
            logger.info(f"MPS available: {self.mps_available}")
            
            if self.mps_available and self.config.device in ['auto', 'mps']:
                self.device = torch.device('mps')
                self.device_name = 'mps'
                self.is_available = True
                
                # Set MPS memory limits
                os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
                
                logger.info("✓ MPS (Metal Performance Shaders) enabled")
                return True
            else:
                self.device = torch.device('cpu')
                self.device_name = 'cpu'
                logger.info("✗ MPS not available, using CPU")
                return False
                
        except ImportError:
            logger.error("PyTorch not installed")
            self.device = None
            return False
    
    def optimize_model(self, model: Any) -> Any:
        """Optimize model for Apple Silicon"""
        if not self.is_available or self.device is None:
            return model
        
        # Move model to MPS
        model = model.to(self.device)
        
        # Enable inference optimizations
        if self.config.enable_optimization:
            model.eval()
            
            # Use torch.compile for PyTorch 2.0+ (significant speedup)
            if hasattr(self.torch, 'compile'):
                try:
                    model = self.torch.compile(model, mode='reduce-overhead')
                    logger.info("✓ torch.compile enabled")
                except Exception as e:
                    logger.warning(f"torch.compile failed: {e}")
        
        return model
    
    def optimize_for_inference(self, model: Any, example_input: Any) -> Any:
        """Optimize model specifically for inference"""
        if not self.is_available:
            return model
        
        model = model.to(self.device)
        model.eval()
        
        # Export to TorchScript for better performance
        try:
            with self.torch.no_grad():
                traced_model = self.torch.jit.trace(model, example_input.to(self.device))
                traced_model = self.torch.jit.optimize_for_inference(traced_model)
                logger.info("✓ TorchScript optimization applied")
                return traced_model
        except Exception as e:
            logger.warning(f"TorchScript optimization failed: {e}")
            return model
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get Apple Silicon specific info"""
        info = super().get_device_info()
        info.update({
            'mps_available': self.mps_available,
            'pytorch_version': self.torch.__version__ if self.torch else None,
            'architecture': platform.machine(),
            'recommendations': [
                'Use torch.compile for 20-30% speedup',
                'Enable PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0',
                'Consider CoreML conversion for production'
            ]
        })
        return info


# =============================================================================
# Windows Optimizations (CUDA / DirectML)
# =============================================================================

class WindowsOptimizer(PlatformOptimizer):
    """Windows optimizations using CUDA or DirectML"""
    
    def __init__(self, config: MLPlatformConfig):
        super().__init__(config)
        self.torch = None
        self.cuda_available = False
        self.directml_available = False
        self.preferred_backend = None
    
    def setup(self) -> bool:
        """Setup CUDA or DirectML for Windows"""
        try:
            import torch
            self.torch = torch
            
            # Check CUDA availability
            self.cuda_available = torch.cuda.is_available()
            
            if self.cuda_available and self.config.device in ['auto', 'cuda']:
                self.device = torch.device('cuda')
                self.device_name = f'cuda:{torch.cuda.get_device_name(0)}'
                self.is_available = True
                self.preferred_backend = 'cuda'
                
                # Enable TF32 for faster training on Ampere+
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                
                logger.info(f"✓ CUDA enabled: {torch.cuda.get_device_name(0)}")
                logger.info(f"  CUDA version: {torch.version.cuda}")
                logger.info(f"  cuDNN version: {torch.backends.cudnn.version()}")
                return True
            
            # Check DirectML as fallback
            elif self.config.device in ['auto', 'directml']:
                return self._setup_directml()
            
            else:
                self.device = torch.device('cpu')
                self.device_name = 'cpu'
                logger.info("✗ CUDA not available, using CPU")
                return False
                
        except ImportError:
            logger.error("PyTorch not installed")
            return False
    
    def _setup_directml(self) -> bool:
        """Setup DirectML for Windows"""
        try:
            import torch_directml
            self.directml_available = True
            self.device = torch_directml.device()
            self.device_name = 'directml'
            self.is_available = True
            self.preferred_backend = 'directml'
            
            logger.info("✓ DirectML enabled")
            return True
        except ImportError:
            logger.warning("torch-directml not installed")
            self.device = self.torch.device('cpu')
            self.device_name = 'cpu'
            return False
    
    def optimize_model(self, model: Any) -> Any:
        """Optimize model for Windows"""
        if not self.is_available or self.device is None:
            return model
        
        # Move model to device
        model = model.to(self.device)
        
        if self.config.enable_optimization:
            model.eval()
            
            # CUDA-specific optimizations
            if self.preferred_backend == 'cuda':
                # Enable cudnn benchmarking
                self.torch.backends.cudnn.benchmark = True
                
                # Use Automatic Mixed Precision if requested
                if self.config.precision == 'fp16':
                    logger.info("✓ Automatic Mixed Precision enabled")
            
            # torch.compile for PyTorch 2.0+
            if hasattr(self.torch, 'compile'):
                try:
                    model = self.torch.compile(model, mode='reduce-overhead')
                    logger.info("✓ torch.compile enabled")
                except Exception as e:
                    logger.warning(f"torch.compile failed: {e}")
        
        return model
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get Windows device info"""
        info = super().get_device_info()
        info.update({
            'cuda_available': self.cuda_available,
            'directml_available': self.directml_available,
            'preferred_backend': self.preferred_backend,
            'pytorch_version': self.torch.__version__ if self.torch else None,
        })
        
        if self.cuda_available:
            info.update({
                'cuda_version': self.torch.version.cuda,
                'cudnn_version': self.torch.backends.cudnn.version(),
                'gpu_name': self.torch.cuda.get_device_name(0),
                'gpu_memory': f"{self.torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB"
            })
        
        return info


# =============================================================================
# CPU Optimizations (Fallback)
# =============================================================================

class CPUOptimizer(PlatformOptimizer):
    """CPU optimizations using OpenMP/MKL"""
    
    def __init__(self, config: MLPlatformConfig):
        super().__init__(config)
        self.torch = None
    
    def setup(self) -> bool:
        """Setup CPU optimizations"""
        try:
            import torch
            self.torch = torch
            
            self.device = torch.device('cpu')
            self.device_name = 'cpu'
            self.is_available = True
            
            # Set thread count
            if self.config.num_threads > 0:
                torch.set_num_threads(self.config.num_threads)
            
            # Enable MKL-DNN if available
            if hasattr(torch, 'backends') and hasattr(torch.backends, 'mkldnn'):
                torch.backends.mkldnn.enabled = True
                logger.info("✓ MKL-DNN enabled")
            
            logger.info(f"✓ CPU mode: {torch.get_num_threads()} threads")
            return True
            
        except ImportError:
            logger.error("PyTorch not installed")
            return False
    
    def optimize_model(self, model: Any) -> Any:
        """Optimize model for CPU inference"""
        model = model.to(self.device)
        model.eval()
        
        # Convert to TorchScript for better CPU performance
        try:
            example_input = self.torch.randn(1, 80, 3000)  # Adjust for your model
            traced_model = self.torch.jit.trace(model, example_input)
            logger.info("✓ TorchScript optimization applied")
            return traced_model
        except Exception as e:
            logger.warning(f"TorchScript optimization failed: {e}")
            return model
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get CPU device info"""
        info = super().get_device_info()
        info.update({
            'num_threads': self.torch.get_num_threads() if self.torch else 0,
            'mkldnn_available': self.torch.backends.mkldnn.is_available() if self.torch and hasattr(self.torch.backends, 'mkldnn') else False,
        })
        return info


# =============================================================================
# Model-Specific Optimizations
# =============================================================================

class WhisperOptimizer:
    """Optimizations for OpenAI Whisper models"""
    
    @staticmethod
    def optimize_for_platform(model: Any, platform: str, config: MLPlatformConfig) -> Any:
        """Apply Whisper-specific optimizations"""
        import torch
        
        if platform.startswith('macos'):
            # Apple Silicon optimizations for Whisper
            if config.precision == 'fp16' and hasattr(model, 'encoder'):
                # Whisper encoder benefits from FP16 on MPS
                model.encoder = model.encoder.half()
                logger.info("✓ Whisper encoder set to FP16")
        
        elif platform == 'windows':
            # Windows CUDA optimizations
            if config.precision == 'fp16':
                logger.info("✓ Using Automatic Mixed Precision for Whisper")
        
        return model


class TranslationModelOptimizer:
    """Optimizations for translation models"""
    
    @staticmethod
    def optimize_for_platform(model: Any, platform: str, config: MLPlatformConfig) -> Any:
        """Apply translation model optimizations"""
        import torch
        
        # Enable gradient checkpointing for memory efficiency
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable()
            logger.info("✓ Gradient checkpointing enabled")
        
        return model


# =============================================================================
# Factory and Utilities
# =============================================================================

def get_platform() -> str:
    """Detect platform"""
    system = platform.system()
    machine = platform.machine()
    
    if system == 'Darwin':
        if 'arm' in machine.lower() or 'aarch64' in machine.lower():
            return 'macos_apple_silicon'
        return 'macos_intel'
    elif system == 'Windows':
        return 'windows'
    return 'unknown'


def create_optimizer(config: Optional[MLPlatformConfig] = None) -> PlatformOptimizer:
    """Factory to create appropriate optimizer"""
    config = config or MLPlatformConfig()
    platform = get_platform()
    
    if platform.startswith('macos'):
        optimizer = AppleSiliconOptimizer(config)
    elif platform == 'windows':
        optimizer = WindowsOptimizer(config)
    else:
        optimizer = CPUOptimizer(config)
    
    optimizer.setup()
    return optimizer


def get_optimal_batch_size(platform: str, model_size: str = "base") -> int:
    """Get optimal batch size for platform and model"""
    recommendations = {
        'macos_apple_silicon': {
            'tiny': 8,
            'base': 4,
            'small': 2,
            'medium': 1,
            'large': 1
        },
        'macos_intel': {
            'tiny': 4,
            'base': 2,
            'small': 1,
            'medium': 1,
            'large': 1
        },
        'windows': {
            'tiny': 16,
            'base': 8,
            'small': 4,
            'medium': 2,
            'large': 1
        }
    }
    
    return recommendations.get(platform, recommendations['windows']).get(model_size, 1)


def print_system_info():
    """Print comprehensive system information"""
    platform_type = get_platform()
    
    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    print(f"Platform: {platform_type}")
    print(f"Python: {sys.version}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    
    # PyTorch info
    try:
        import torch
        print(f"\nPyTorch: {torch.__version__}")
        
        if platform_type.startswith('macos'):
            print(f"MPS available: {torch.backends.mps.is_available()}")
            print(f"MPS built: {torch.backends.mps.is_built()}")
        
        elif platform_type == 'windows':
            print(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"CUDA version: {torch.version.cuda}")
                print(f"GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("\nPyTorch: Not installed")
    
    # ONNX Runtime info
    try:
        import onnxruntime as ort
        print(f"\nONNX Runtime: {ort.__version__}")
        print(f"Available providers: {ort.get_available_providers()}")
    except ImportError:
        print("\nONNX Runtime: Not installed")
    
    print("=" * 60)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Print system info
    print_system_info()
    
    # Create optimizer
    config = MLPlatformConfig(device='auto', precision='fp32')
    optimizer = create_optimizer(config)
    
    # Print device info
    print("\nDevice Info:")
    info = optimizer.get_device_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
