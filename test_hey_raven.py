#!/usr/bin/env python3
"""
Simple Hey Raven Test Script
Tests the core functionality without requiring all services to be running.
"""

import asyncio
import json
import time
from datetime import datetime, timezone

# Test imports
try:
    from services.llm_processor.llm_client import OllamaClient
    from services.llm_processor.language_manager import language_manager
    from services.tts_processor.tts_engine import RavenTTSEngine
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the raven_api directory and venv is activated")
    exit(1)

async def test_llm_client():
    """Test LLM client functionality."""
    print("\n🧠 Testing LLM Client...")
    
    try:
        client = OllamaClient()
        
        # Test model availability
        model_ready = await client.check_model_availability()
        if model_ready:
            print("✅ Ollama model is available")
            
            # Test response generation
            response = await client.generate_response(
                "Hello Raven, what time is it?", 
                test_mode=True
            )
            print(f"✅ LLM Response: {response}")
        else:
            print("⚠️  Ollama model not available - install Ollama and pull mistral:7b")
            
    except Exception as e:
        print(f"❌ LLM test failed: {e}")

def test_language_detection():
    """Test language detection."""
    print("\n🌍 Testing Language Detection...")
    
    test_phrases = [
        "Hey Raven, what time is it?",
        "Hola Raven, ¿qué hora es?",
        "Bonjour Raven, quelle heure est-il?",
        "Hallo Raven, wie spät ist es?"
    ]
    
    for phrase in test_phrases:
        lang, confidence = language_manager.detect_language(phrase)
        print(f"✅ '{phrase}' → {lang} (confidence: {confidence:.2f})")

def test_tts_engine():
    """Test TTS engine."""
    print("\n🔊 Testing TTS Engine...")
    
    try:
        engine = RavenTTSEngine()
        
        # Test TTS generation
        test_text = "Hello, this is a test of the Hey Raven TTS system."
        audio_data = engine.generate_speech(test_text)
        
        if audio_data:
            print(f"✅ TTS generated {len(audio_data)} bytes of audio")
        else:
            print("❌ TTS generation failed")
            
    except Exception as e:
        print(f"❌ TTS test failed: {e}")

def test_wake_word_patterns():
    """Test wake word patterns."""
    print("\n🎤 Testing Wake Word Patterns...")
    
    test_phrases = [
        "Hey Raven, can you help me?",
        "Hello Raven, what's the weather?",
        "Raven, what time is it?",
        "Hey Raven, summarize this meeting",
        "This is not a wake word",
        "Just talking normally"
    ]
    
    for phrase in test_phrases:
        lang, confidence = language_manager.detect_language(phrase)
        config = language_manager.get_language_config(lang)
        
        # Check if any wake word is in the phrase
        wake_word_found = any(
            wake_word.lower() in phrase.lower() 
            for wake_word in config.wake_words
        )
        
        status = "✅ WAKE WORD" if wake_word_found else "❌ Not detected"
        print(f"{status}: '{phrase}'")

async def test_end_to_end_simulation():
    """Simulate end-to-end workflow."""
    print("\n🔄 Testing End-to-End Simulation...")
    
    try:
        # Simulate wake word detection
        question = "Hey Raven, what time is it?"
        print(f"1. Wake word detected: '{question}'")
        
        # Simulate LLM processing
        client = OllamaClient()
        if await client.check_model_availability():
            response = await client.generate_response(question, test_mode=True)
            print(f"2. LLM Response: '{response}'")
            
            # Simulate TTS generation
            engine = RavenTTSEngine()
            audio_data = engine.generate_speech(response)
            if audio_data:
                print(f"3. TTS Audio: {len(audio_data)} bytes generated")
                print("✅ End-to-end simulation successful!")
            else:
                print("❌ TTS generation failed")
        else:
            print("⚠️  Skipping LLM test - Ollama not available")
            
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")

def print_system_info():
    """Print system information."""
    print("🎯 Hey Raven System Test")
    print("=" * 50)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Python: {__import__('sys').version}")
    
    # Check available services
    services = {
        "Redis": "redis",
        "Ollama": "requests", 
        "TTS": "gtts",
        "Audio": "pydub"
    }
    
    print("\n📦 Service Dependencies:")
    for service, module in services.items():
        try:
            __import__(module)
            print(f"✅ {service}: Available")
        except ImportError:
            print(f"❌ {service}: Not available")

async def main():
    """Main test function."""
    print_system_info()
    
    # Run tests
    test_language_detection()
    test_wake_word_patterns()
    test_tts_engine()
    await test_llm_client()
    await test_end_to_end_simulation()
    
    print("\n🎉 Hey Raven Test Complete!")
    print("\n📋 Next Steps:")
    print("1. Install Ollama: https://ollama.ai/")
    print("2. Pull model: ollama pull mistral:7b")
    print("3. Start Redis: redis-server")
    print("4. Run full services: python services/llm-processor/main.py")

if __name__ == "__main__":
    asyncio.run(main())


