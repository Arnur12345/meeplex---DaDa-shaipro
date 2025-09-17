#!/usr/bin/env python3
"""
Hey Raven Configuration Validator
Validates environment configuration for all services before deployment.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import redis
import requests
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfigValidator:
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validations: List[str] = []
        
    def load_env(self):
        """Load environment variables from file if specified."""
        if self.env_file and os.path.exists(self.env_file):
            logger.info(f"Loading environment from {self.env_file}")
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
                        
    def add_error(self, message: str):
        """Add validation error."""
        self.errors.append(f"❌ ERROR: {message}")
        logger.error(message)
        
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(f"⚠️  WARNING: {message}")
        logger.warning(message)
        
    def add_validation(self, message: str):
        """Add successful validation."""
        self.validations.append(f"✅ {message}")
        logger.info(message)

    def validate_redis_config(self) -> bool:
        """Validate Redis configuration and connectivity."""
        logger.info("🔍 Validating Redis configuration...")
        
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))
        
        try:
            # Test Redis connection
            r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, socket_timeout=5)
            r.ping()
            self.add_validation(f"Redis connection successful: {redis_host}:{redis_port}/{redis_db}")
            
            # Check Redis streams
            streams_to_check = [
                os.getenv('REDIS_INPUT_STREAM_NAME', 'hey_raven_commands'),
                os.getenv('REDIS_OUTPUT_STREAM_NAME', 'llm_responses'),
                os.getenv('TTS_AUDIO_STREAM_NAME', 'tts_audio_queue')
            ]
            
            for stream in streams_to_check:
                try:
                    r.xinfo_stream(stream)
                    self.add_validation(f"Redis stream exists: {stream}")
                except redis.exceptions.ResponseError:
                    self.add_warning(f"Redis stream does not exist (will be created): {stream}")
                    
            return True
            
        except redis.exceptions.ConnectionError:
            self.add_error(f"Cannot connect to Redis at {redis_host}:{redis_port}")
            return False
        except Exception as e:
            self.add_error(f"Redis validation failed: {str(e)}")
            return False

    def validate_ollama_config(self) -> bool:
        """Validate Ollama configuration and connectivity."""
        logger.info("🔍 Validating Ollama configuration...")
        
        ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
        ollama_port = os.getenv('OLLAMA_PORT', '11434')
        ollama_model = os.getenv('OLLAMA_MODEL', 'mistral:7b')
        
        try:
            # Test Ollama API connection
            ollama_url = f"http://{ollama_host}:{ollama_port}/api/tags"
            response = requests.get(ollama_url, timeout=10)
            response.raise_for_status()
            
            self.add_validation(f"Ollama API connection successful: {ollama_host}:{ollama_port}")
            
            # Check if model is available
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            
            if ollama_model in available_models:
                self.add_validation(f"Ollama model available: {ollama_model}")
            else:
                self.add_warning(f"Ollama model not found: {ollama_model}. Available models: {available_models}")
                
            return True
            
        except requests.exceptions.RequestException:
            self.add_error(f"Cannot connect to Ollama at {ollama_host}:{ollama_port}")
            return False
        except Exception as e:
            self.add_error(f"Ollama validation failed: {str(e)}")
            return False

    def validate_stream_config(self) -> bool:
        """Validate Redis stream configuration consistency."""
        logger.info("🔍 Validating stream configuration consistency...")
        
        # LLM Processor streams
        llm_input = os.getenv('REDIS_INPUT_STREAM_NAME', 'hey_raven_commands')
        llm_output = os.getenv('REDIS_OUTPUT_STREAM_NAME', 'llm_responses')
        
        # TTS Processor streams  
        tts_input = os.getenv('REDIS_INPUT_STREAM_NAME', 'llm_responses')  # Should match LLM output
        tts_output = os.getenv('REDIS_OUTPUT_STREAM_NAME', 'tts_audio_queue')
        
        # Vexa-Bot stream
        audio_stream = os.getenv('TTS_AUDIO_STREAM_NAME', 'tts_audio_queue')  # Should match TTS output
        
        if llm_output == tts_input:
            self.add_validation(f"LLM→TTS stream configuration consistent: {llm_output}")
        else:
            self.add_error(f"LLM output stream ({llm_output}) != TTS input stream ({tts_input})")
            
        if tts_output == audio_stream:
            self.add_validation(f"TTS→Vexa stream configuration consistent: {tts_output}")
        else:
            self.add_error(f"TTS output stream ({tts_output}) != Vexa audio stream ({audio_stream})")
            
        return len(self.errors) == 0

    def validate_wake_word_config(self) -> bool:
        """Validate wake word configuration."""
        logger.info("🔍 Validating wake word configuration...")
        
        config_path = os.getenv('WAKE_WORD_CONFIG_PATH', '/app/config/wake_word_config.json')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                required_sections = ['patterns', 'sensitivity', 'rate_limiting', 'extraction']
                for section in required_sections:
                    if section in config:
                        self.add_validation(f"Wake word config section present: {section}")
                    else:
                        self.add_warning(f"Wake word config section missing: {section}")
                        
                return True
                
            except json.JSONDecodeError as e:
                self.add_error(f"Wake word config JSON invalid: {str(e)}")
                return False
        else:
            self.add_warning(f"Wake word config file not found: {config_path}")
            return True

    def validate_docker_config(self) -> bool:
        """Validate Docker configuration."""
        logger.info("🔍 Validating Docker configuration...")
        
        # Check if docker-compose.yml exists
        compose_file = Path("docker-compose.yml")
        if compose_file.exists():
            self.add_validation("Docker Compose file exists")
        else:
            self.add_error("Docker Compose file not found")
            
        # Check environment variables
        required_env_vars = [
            'REDIS_HOST', 'OLLAMA_HOST', 'FASTAPI_HOST'
        ]
        
        for var in required_env_vars:
            if os.getenv(var):
                self.add_validation(f"Environment variable set: {var}")
            else:
                self.add_warning(f"Environment variable not set: {var}")
                
        return True

    def validate_performance_config(self) -> bool:
        """Validate performance-related configuration."""
        logger.info("🔍 Validating performance configuration...")
        
        # Check timeout settings
        ollama_timeout = int(os.getenv('OLLAMA_API_TIMEOUT', '60'))
        tts_timeout = int(os.getenv('TTS_TIMEOUT', '10'))
        
        if ollama_timeout >= 30:
            self.add_validation(f"Ollama timeout reasonable: {ollama_timeout}s")
        else:
            self.add_warning(f"Ollama timeout may be too low: {ollama_timeout}s")
            
        if tts_timeout >= 5:
            self.add_validation(f"TTS timeout reasonable: {tts_timeout}s")
        else:
            self.add_warning(f"TTS timeout may be too low: {tts_timeout}s")
            
        # Check response limits
        max_response_length = int(os.getenv('MAX_RESPONSE_LENGTH', '500'))
        max_text_length = int(os.getenv('MAX_TEXT_LENGTH', '1000'))
        
        if max_response_length <= max_text_length:
            self.add_validation("Response length limits consistent")
        else:
            self.add_warning("Response length limit exceeds TTS text limit")
            
        return True

    def run_validation(self) -> bool:
        """Run complete validation suite."""
        logger.info("🚀 Starting Hey Raven configuration validation...")
        
        self.load_env()
        
        validation_functions = [
            self.validate_redis_config,
            self.validate_ollama_config,
            self.validate_stream_config,
            self.validate_wake_word_config,
            self.validate_docker_config,
            self.validate_performance_config
        ]
        
        success = True
        for validation_func in validation_functions:
            try:
                result = validation_func()
                if not result:
                    success = False
            except Exception as e:
                self.add_error(f"Validation function {validation_func.__name__} failed: {str(e)}")
                success = False
                
        # Print results
        print("\n" + "="*60)
        print("🎯 Hey Raven Configuration Validation Results")
        print("="*60)
        
        if self.validations:
            print(f"\n✅ VALIDATIONS PASSED ({len(self.validations)}):")
            for validation in self.validations:
                print(f"  {validation}")
                
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")
                
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
            print(f"\n❌ VALIDATION FAILED: {len(self.errors)} errors found")
            success = False
        else:
            print(f"\n🎉 VALIDATION SUCCESSFUL: All critical checks passed!")
            
        print("="*60)
        return success

def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate Hey Raven configuration')
    parser.add_argument('--env-file', '-e', help='Environment file to load')
    parser.add_argument('--strict', '-s', action='store_true', help='Fail on warnings')
    
    args = parser.parse_args()
    
    validator = ConfigValidator(args.env_file)
    success = validator.run_validation()
    
    if args.strict and validator.warnings:
        print("⚠️  Strict mode: Failing due to warnings")
        success = False
        
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()


