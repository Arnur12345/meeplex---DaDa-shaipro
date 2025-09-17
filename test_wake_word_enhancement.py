#!/usr/bin/env python3
"""
Test script for Enhanced Wake Word Detection in RavenAI
Demonstrates the new patterns, fuzzy matching, and rate limiting features.
"""

import sys
import os
import json
from datetime import datetime, timezone

# Add the transcription-collector to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'transcription-collector'))

from streaming.processors import WakeWordDetector

def test_wake_word_patterns():
    """Test various wake word patterns and scenarios."""
    
    print("=" * 60)
    print("Enhanced Wake Word Detection Test Suite")
    print("=" * 60)
    print()
    
    # Initialize detector
    detector = WakeWordDetector()
    
    # Test cases
    test_cases = [
        # Primary patterns
        ("hey raven what time is it?", "primary"),
        ("hello raven can you help me?", "primary"), 
        ("hi raven where am I?", "primary"),
        
        # Secondary patterns
        ("okay raven tell me about the weather", "secondary"),
        ("excuse me raven how do I get there?", "secondary"),
        ("raven what is the status?", "secondary"),
        
        # Conversational patterns
        ("raven can you explain this to me?", "conversational"),
        ("raven help me with this problem", "conversational"),
        ("raven tell me what you think", "conversational"),
        
        # Question patterns
        ("raven what is happening here?", "question"),
        ("raven where should I go?", "question"),
        ("raven how does this work?", "question"),
        ("raven why is this not working?", "question"),
        ("raven when will this be done?", "question"),
        ("raven who is responsible for this?", "question"),
        
        # Punctuation patterns
        ("raven, can you help?", "punctuation"),
        ("raven?", "punctuation"),
        
        # Fuzzy matching (ASR errors)
        ("hey haven what time is it?", "fuzzy"),
        ("hello haven can you help?", "fuzzy"),
        
        # Should NOT match
        ("this is just a regular sentence", None),
        ("talking about a raven bird", None),
        ("haven't seen it", None),
        ("hey there", None),
    ]
    
    print("Testing Wake Word Pattern Detection:")
    print("-" * 40)
    
    detected_count = 0
    total_count = len(test_cases)
    
    for i, (text, expected_category) in enumerate(test_cases, 1):
        print(f"{i:2d}. Testing: '{text}'")
        
        detected_question = detector.detect_and_extract(text, f"test_session_{i}")
        
        if detected_question:
            detected_count += 1
            print(f"    ✅ DETECTED: '{detected_question}'")
            if expected_category:
                print(f"    📝 Expected category: {expected_category}")
            else:
                print(f"    ⚠️  Unexpected detection (should not match)")
        else:
            if expected_category:
                print(f"    ❌ NOT DETECTED (expected {expected_category})")
            else:
                print(f"    ✅ NOT DETECTED (correct - should not match)")
        print()
    
    print("=" * 60)
    print(f"Test Results: {detected_count}/{total_count} patterns tested")
    print("=" * 60)
    print()

def test_rate_limiting():
    """Test rate limiting functionality."""
    
    print("Testing Rate Limiting:")
    print("-" * 40)
    
    detector = WakeWordDetector()
    session_id = "rate_limit_test_session"
    
    # Test rapid fire detections
    print("1. Testing rapid fire detections (should be rate limited):")
    for i in range(5):
        result = detector.detect_and_extract("hey raven what time is it?", session_id)
        if result:
            print(f"   Detection {i+1}: ✅ '{result}'")
        else:
            print(f"   Detection {i+1}: ⏸️  Rate limited")
    
    print()
    print("2. Testing different sessions (should not be rate limited):")
    for i in range(3):
        session_id = f"session_{i}"
        result = detector.detect_and_extract("hey raven what time is it?", session_id)
        if result:
            print(f"   Session {i+1}: ✅ '{result}'")
        else:
            print(f"   Session {i+1}: ❌ Failed")
    
    print()

def display_configuration():
    """Display current configuration."""
    
    print("Current Configuration:")
    print("-" * 40)
    
    detector = WakeWordDetector()
    config = detector.config
    
    print("Patterns:")
    for category, patterns in config.get("patterns", {}).items():
        if isinstance(patterns, list):
            print(f"  {category.capitalize()}: {len(patterns)} patterns")
            for pattern in patterns:
                print(f"    - {pattern}")
        else:
            print(f"  {category.capitalize()}: {patterns}")
    print()
    
    print("Sensitivity Settings:")
    sensitivity = config.get("sensitivity", {})
    for key, value in sensitivity.items():
        print(f"  {key}: {value}")
    print()
    
    print("Rate Limiting:")
    rate_limiting = config.get("rate_limiting", {})
    for key, value in rate_limiting.items():
        print(f"  {key}: {value}")
    print()

def main():
    """Main test function."""
    
    print(f"Enhanced Wake Word Detection Test")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    try:
        display_configuration()
        test_wake_word_patterns()
        test_rate_limiting()
        
        print("✅ All tests completed successfully!")
        print()
        print("To test in the live system:")
        print("1. Start services: make up")
        print("2. Send transcription with wake words")
        print("3. Monitor logs: make logs | grep 'WakeWord Detected'")
        print("4. Check Redis streams: make llm-streams")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


