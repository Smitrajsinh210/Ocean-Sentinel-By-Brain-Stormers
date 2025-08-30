"""
Ocean Sentinel - Utilities Package
Common utility modules for the Ocean Sentinel backend
"""

import logging
from typing import Dict, Any

# Set up logging for utilities
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

utils_logger = logging.getLogger('ocean_sentinel.utils')

__version__ = "1.0.0"
__author__ = "Ocean Sentinel Team"

# Import main utility classes
try:
    from .blockchain_utils import blockchain_utils, BlockchainUtils, BlockchainRecord, DataIntegrityResult
    utils_logger.info("✅ Blockchain utilities loaded")
except ImportError as e:
    utils_logger.warning(f"⚠️  Blockchain utilities not available: {str(e)}")
    blockchain_utils = None
    BlockchainUtils = None
    BlockchainRecord = None
    DataIntegrityResult = None

# Utility functions
def validate_environment() -> Dict[str, bool]:
    """Validate required environment variables"""
    import os
    
    required_vars = {
        'SUPABASE_URL': bool(os.getenv('SUPABASE_URL')),
        'SUPABASE_ANON_KEY': bool(os.getenv('SUPABASE_ANON_KEY')),
        'OPENWEATHER_API_KEY': bool(os.getenv('OPENWEATHER_API_KEY')),
    }
    
    optional_vars = {
        'STARTON_API_KEY': bool(os.getenv('STARTON_API_KEY')),
        'CONTRACT_ADDRESS': bool(os.getenv('CONTRACT_ADDRESS')),
        'GOOGLE_AI_STUDIO_KEY': bool(os.getenv('GOOGLE_AI_STUDIO_KEY')),
        'OPENAQ_API_KEY': bool(os.getenv('OPENAQ_API_KEY')),
        'NASA_API_KEY': bool(os.getenv('NASA_API_KEY')),
    }
    
    return {
        'required': required_vars,
        'optional': optional_vars,
        'all_required_present': all(required_vars.values())
    }

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    import platform
    import sys
    import os
    from datetime import datetime
    
    return {
        'platform': platform.platform(),
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'timestamp': datetime.now().isoformat(),
        'environment_validation': validate_environment()
    }

# Export main utilities
__all__ = [
    'blockchain_utils',
    'BlockchainUtils', 
    'BlockchainRecord',
    'DataIntegrityResult',
    'validate_environment',
    'get_system_info',
    'utils_logger'
]

utils_logger.info("Ocean Sentinel utilities package initialized")