"""
Settings Manager for Audio Auto-Tune

Handles persistence of audio profiles with migration support.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from platformdirs import user_config_dir

logger = logging.getLogger(__name__)


@dataclass
class AudioProfile:
    """Optimized audio settings profile for a device."""
    device_id: int
    device_name: str
    gain_mode: str  # 'hardware', 'digital', 'unknown'
    gain_db: float
    digital_multiplier: float
    noise_floor_db: float
    peak_level_db: float
    rms_level_db: float
    snr_db: float
    sample_rate: int
    timestamp: str
    confidence_score: float
    platform: str = field(default="")
    profile_version: str = field(default="2.2.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioProfile':
        """Create from dictionary."""
        # Handle missing fields for migration
        defaults = {
            'platform': '',
            'profile_version': '2.1.0',
            'gain_mode': 'unknown',
            'digital_multiplier': 1.0
        }
        
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SettingsManager:
    """
    Manage audio profiles with persistence and migration.
    
    Features:
    - Save/load profiles to user config directory
    - Automatic profile migration from older versions
    - Per-device profile management
    - JSON-based storage
    """
    
    CURRENT_PROFILE_VERSION = "2.2.0"
    CONFIG_FILENAME = "audio_profiles.json"
    
    def __init__(self, app_name: str = "voicetranslate", 
                 app_author: str = "jimmywong"):
        """
        Initialize settings manager.
        
        Args:
            app_name: Application name for config directory
            app_author: Application author for config directory
        """
        self.app_name = app_name
        self.app_author = app_author
        
        # Get platform-specific config directory
        self.config_dir = Path(user_config_dir(app_name, app_author))
        self.config_file = self.config_dir / self.CONFIG_FILENAME
        
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Settings directory: {self.config_dir}")
    
    def load_profiles(self) -> List[AudioProfile]:
        """
        Load profiles from storage with migration.
        
        Returns:
            List of AudioProfile objects
        """
        if not self.config_file.exists():
            logger.info("No profile file found, starting fresh")
            return []
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            
            # Check version
            file_version = data.get('profile_version', '2.1.0')
            profiles_data = data.get('profiles', [])
            
            # Migrate if needed
            if file_version != self.CURRENT_PROFILE_VERSION:
                profiles_data = self._migrate_profiles(profiles_data, file_version)
            
            # Convert to objects
            profiles = [AudioProfile.from_dict(p) for p in profiles_data]
            
            logger.info(f"Loaded {len(profiles)} profile(s) (version {file_version})")
            return profiles
            
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted profile file: {e}")
            # Backup corrupted file
            backup_path = self.config_file.with_suffix('.json.bak')
            self.config_file.rename(backup_path)
            logger.info(f"Backed up corrupted file to {backup_path}")
            return []
            
        except Exception as e:
            logger.error(f"Error loading profiles: {e}")
            return []
    
    def save_profiles(self, profiles: List[AudioProfile]):
        """
        Save profiles to storage.
        
        Args:
            profiles: List of AudioProfile objects
        """
        data = {
            'profile_version': self.CURRENT_PROFILE_VERSION,
            'saved_at': datetime.now().isoformat(),
            'profiles': [p.to_dict() for p in profiles]
        }
        
        try:
            # Write to temp file first
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            temp_file.rename(self.config_file)
            
            logger.info(f"Saved {len(profiles)} profile(s)")
            
        except Exception as e:
            logger.error(f"Error saving profiles: {e}")
            raise
    
    def _migrate_profiles(self, profiles_data: List[Dict], 
                         from_version: str) -> List[Dict]:
        """
        Migrate profiles from older versions.
        
        Args:
            profiles_data: List of profile dictionaries
            from_version: Version string of the data
            
        Returns:
            Migrated profile data
        """
        logger.info(f"Migrating profiles from v{from_version} to v{self.CURRENT_PROFILE_VERSION}")
        
        for profile in profiles_data:
            # Migration from 2.1.0 to 2.2.0
            if from_version == '2.1.0':
                if 'gain_mode' not in profile:
                    profile['gain_mode'] = 'unknown'
                if 'digital_multiplier' not in profile:
                    profile['digital_multiplier'] = 1.0
                if 'platform' not in profile:
                    profile['platform'] = ''
                if 'profile_version' not in profile:
                    profile['profile_version'] = '2.1.0'
            
            # Add more migrations as needed
            
            # Update to current version
            profile['profile_version'] = self.CURRENT_PROFILE_VERSION
        
        logger.info(f"Migrated {len(profiles_data)} profile(s)")
        return profiles_data
    
    def get_profile(self, device_id: int) -> Optional[AudioProfile]:
        """
        Get profile for a specific device.
        
        Args:
            device_id: Audio device ID
            
        Returns:
            AudioProfile or None if not found
        """
        profiles = self.load_profiles()
        for profile in profiles:
            if profile.device_id == device_id:
                return profile
        return None
    
    def save_profile(self, profile: AudioProfile):
        """
        Save or update a single profile.
        
        Args:
            profile: AudioProfile to save
        """
        profiles = self.load_profiles()
        
        # Update existing or add new
        updated = False
        for i, p in enumerate(profiles):
            if p.device_id == profile.device_id:
                profiles[i] = profile
                updated = True
                break
        
        if not updated:
            profiles.append(profile)
        
        self.save_profiles(profiles)
        logger.info(f"Saved profile for device {profile.device_id}")
    
    def delete_profile(self, device_id: int):
        """
        Delete profile for a device.
        
        Args:
            device_id: Audio device ID
        """
        profiles = self.load_profiles()
        profiles = [p for p in profiles if p.device_id != device_id]
        self.save_profiles(profiles)
        logger.info(f"Deleted profile for device {device_id}")
    
    def get_active_profile_id(self) -> Optional[int]:
        """Get the currently active profile device ID."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            return data.get('active_profile')
        except Exception:
            return None
    
    def set_active_profile(self, device_id: int):
        """Set the active profile device ID."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            
            data['active_profile'] = device_id
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error setting active profile: {e}")
    
    def get_config_path(self) -> Path:
        """Get the path to the config file."""
        return self.config_file
    
    def export_profiles(self, export_path: Path):
        """Export profiles to a file."""
        profiles = self.load_profiles()
        data = {
            'profile_version': self.CURRENT_PROFILE_VERSION,
            'exported_at': datetime.now().isoformat(),
            'profiles': [p.to_dict() for p in profiles]
        }
        
        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(profiles)} profile(s) to {export_path}")
    
    def import_profiles(self, import_path: Path) -> int:
        """
        Import profiles from a file.
        
        Returns:
            Number of profiles imported
        """
        with open(import_path, 'r') as f:
            data = json.load(f)
        
        imported_profiles = data.get('profiles', [])
        file_version = data.get('profile_version', '2.1.0')
        
        # Migrate if needed
        if file_version != self.CURRENT_PROFILE_VERSION:
            imported_profiles = self._migrate_profiles(imported_profiles, file_version)
        
        # Load existing profiles
        existing_profiles = self.load_profiles()
        existing_ids = {p.device_id for p in existing_profiles}
        
        # Add imported profiles (skip duplicates)
        added = 0
        for profile_data in imported_profiles:
            if profile_data['device_id'] not in existing_ids:
                existing_profiles.append(AudioProfile.from_dict(profile_data))
                added += 1
        
        self.save_profiles(existing_profiles)
        logger.info(f"Imported {added} new profile(s) from {import_path}")
        
        return added
