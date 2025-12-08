"""Profile management for custom routing profiles."""
from pathlib import Path
from typing import Dict, Any, List
import json
from backroads.config import CONFIGS_DIR
from backroads.core.routing.weighting import (
    DEFAULT_SCENIC_BY_TYPE,
    DEFAULT_NATURAL_BY_TYPE,
)


def get_profile_path(profile_name: str) -> Path:
    """Get the file path for a profile."""
    # Sanitize profile name to be filesystem-safe
    safe_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    if not safe_name:
        raise ValueError("Profile name must contain at least one alphanumeric character")
    return CONFIGS_DIR / f"{safe_name}.json"


def load_profile(profile_name: str) -> Dict[str, Any]:
    """Load a profile from disk."""
    if profile_name == "default":
        return {
            "scenic_by_type": dict(DEFAULT_SCENIC_BY_TYPE),
            "natural_by_type": dict(DEFAULT_NATURAL_BY_TYPE),
        }
    
    profile_path = get_profile_path(profile_name)
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile '{profile_name}' not found")
    
    with open(profile_path, 'r') as f:
        return json.load(f)


def save_profile(profile_name: str, scenic_by_type: Dict[str, float], natural_by_type: Dict[str, float]) -> None:
    """Save a profile to disk."""
    if profile_name == "default":
        raise ValueError("Cannot save a profile with name 'default'")
    
    # Ensure CONFIGS_DIR exists
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    
    profile_path = get_profile_path(profile_name)
    profile_data = {
        "name": profile_name,
        "scenic_by_type": scenic_by_type,
        "natural_by_type": natural_by_type,
    }
    
    with open(profile_path, 'w') as f:
        json.dump(profile_data, f, indent=2)


def list_profiles() -> List[str]:
    """List all available profiles."""
    profiles = []
    if not CONFIGS_DIR.exists():
        return profiles
    
    for file_path in CONFIGS_DIR.glob("*.json"):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and "name" in data:
                    profiles.append(data["name"])
        except (json.JSONDecodeError, KeyError):
            # Skip invalid JSON files
            continue
    
    return sorted(profiles)


def initialize_preset_profiles():
    """Initialize preset profiles (mountains, ocean) if they don't exist."""
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Mountains profile - favor mountain/terrain features
    # Values between 0 and 1, with 0.5 as default
    mountains_natural = dict(DEFAULT_NATURAL_BY_TYPE)
    # Boost mountain-related features (0.7-0.9 range)
    mountains_natural.update({
        "peak": 0.9,
        "ridge": 0.85,
        "cliff": 0.85,
        "hill": 0.8,
        "valley": 0.8,
        "bare_rock": 0.8,
        "saddle": 0.8,
        "rock": 0.75,
        "stone": 0.75,
        "scree": 0.75,
        "tree": 0.7,  # Mountains often have trees
        "wood": 0.7,
    })
    
    # Ocean profile - favor coastal/ocean features
    # Values between 0 and 1, with 0.5 as default
    ocean_natural = dict(DEFAULT_NATURAL_BY_TYPE)
    # Boost ocean/coastal features (0.7-0.9 range)
    ocean_natural.update({
        "beach": 0.9,
        "coastline": 0.9,
        "bay": 0.85,
        "cape": 0.85,
        "water": 0.8,
        "arch": 0.8,
        "dune": 0.75,
        "sand": 0.75,
        "cliff": 0.75,  # Coastal cliffs
    })
    
    # Use default scenic weights for both
    mountains_scenic = dict(DEFAULT_SCENIC_BY_TYPE)
    ocean_scenic = dict(DEFAULT_SCENIC_BY_TYPE)
    
    # Create profiles if they don't exist
    for profile_name, scenic, natural in [
        ("mountains", mountains_scenic, mountains_natural),
        ("ocean", ocean_scenic, ocean_natural),
    ]:
        profile_path = get_profile_path(profile_name)
        if not profile_path.exists():
            save_profile(profile_name, scenic, natural)

