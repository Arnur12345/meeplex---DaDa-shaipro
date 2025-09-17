# Hey Raven - Quick Start Guide

## 🚀 **Running Hey Raven on CPU**

### **Prerequisites (Already Done ✅)**
- ✅ Python 3.13.3 installed
- ✅ Virtual environment activated
- ✅ CPU configuration set (`DEVICE_TYPE=cpu`)
- ✅ Whisper model downloaded

### **Step 1: Install Additional Dependencies**

```bash
# Install Ollama (for LLM)
# Download from: https://ollama.ai/
# Then run: ollama pull mistral:7b

# Install Redis (for message queuing)
# Windows: Download from https://redis.io/download
# Or use Docker: docker run -d -p 6379:6379 redis:alpine
```

### **Step 2: Run Individual Services**

#### **Test LLM Processor:**
```bash
cd services/llm-processor
python main.py
```

#### **Test TTS Processor:**
```bash
cd services/tts-processor  
python main.py
```

#### **Test Transcription Collector:**
```bash
cd services/transcription-collector
python main.py
```

### **Step 3: Run Full System with Docker**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### **Step 4: Test the System**

```bash
# Run the test script
python test_hey_raven.py

# Test wake word detection
python test_wake_word_enhancement.py
```

## 🔧 **Troubleshooting**

### **If you get CUDA errors:**
- Make sure `DEVICE_TYPE=cpu` in `.env` file
- Check that `download_model.py` uses `'cpu'` as default

### **If Ollama is not available:**
- Install Ollama from https://ollama.ai/
- Run: `ollama pull mistral:7b`

### **If Redis is not available:**
- Install Redis or use Docker: `docker run -d -p 6379:6379 redis:alpine`

## 📋 **Quick Commands**

```bash
# Activate virtual environment
.\venv\bin\Activate.ps1

# Test everything
python test_hey_raven.py

# Run LLM service
cd services/llm-processor && python main.py

# Run TTS service  
cd services/tts-processor && python main.py

# Run with Docker
docker-compose up -d
```

## 🎯 **What Each Service Does**

1. **transcription-collector**: Detects "Hey Raven" wake words
2. **llm-processor**: Generates intelligent responses using Ollama
3. **tts-processor**: Converts text to speech
4. **vexa-bot**: Joins meetings and plays audio responses
5. **bot-manager**: Orchestrates bot deployment

## 🚀 **Next Steps**

1. Install Ollama and pull mistral:7b model
2. Start Redis server
3. Run individual services to test
4. Use Docker Compose for full deployment
5. Test with actual meeting URLs

---

**The CUDA issue is now fixed!** Your system is configured to run on CPU. 🎉


