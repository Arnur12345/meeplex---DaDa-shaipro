/**
 * Advanced Audio Features for Hey Raven Vexa-Bot
 * Includes voice activity detection, noise suppression, and audio quality enhancements
 */

// Audio enhancement configuration
export interface AudioConfig {
  enableNoiseSupression: boolean;
  enableVoiceActivityDetection: boolean;
  enableAudioLevelMeter: boolean;
  microphoneGain: number;
  speakerVolume: number;
  sampleRate: number;
  bufferSize: number;
}

export interface VoiceActivityResult {
  isVoiceDetected: boolean;
  confidence: number;
  audioLevel: number;
  timestamp: number;
}

export class AudioEnhancementManager {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private isInitialized = false;
  private config: AudioConfig;
  
  // Voice activity detection
  private voiceThreshold = 0.01;
  private silenceThreshold = 0.005;
  private voiceActivityBuffer: number[] = [];
  private bufferSize = 10;
  
  // Audio level monitoring
  private currentAudioLevel = 0;
  private maxAudioLevel = 0;
  private audioLevelHistory: number[] = [];
  
  constructor(config: Partial<AudioConfig> = {}) {
    this.config = {
      enableNoiseSupression: true,
      enableVoiceActivityDetection: true,
      enableAudioLevelMeter: true,
      microphoneGain: 1.0,
      speakerVolume: 1.0,
      sampleRate: 16000,
      bufferSize: 1024,
      ...config
    };
  }

  async initialize(mediaStream: MediaStream): Promise<boolean> {
    try {
      (window as any).logBot?.('[Audio Enhancement] Initializing audio enhancements...');
      
      // Initialize Web Audio API
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.sampleRate
      });
      
      // Create audio source from microphone
      this.microphone = this.audioContext.createMediaStreamSource(mediaStream);
      
      // Create analyser for audio level detection
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.8;
      
      // Create script processor for real-time analysis
      this.processor = this.audioContext.createScriptProcessor(this.config.bufferSize, 1, 1);
      
      // Connect audio nodes
      this.microphone.connect(this.analyser);
      this.analyser.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      
      // Setup audio processing
      this.processor.onaudioprocess = (event) => this.processAudio(event);
      
      this.isInitialized = true;
      (window as any).logBot?.('[Audio Enhancement] ✅ Audio enhancements initialized');
      
      return true;
    } catch (error) {
      (window as any).logBot?.(`[Audio Enhancement] ❌ Failed to initialize: ${error}`);
      return false;
    }
  }

  private processAudio(event: AudioProcessingEvent): void {
    if (!this.config.enableVoiceActivityDetection && !this.config.enableAudioLevelMeter) {
      return;
    }

    const inputBuffer = event.inputBuffer;
    const inputData = inputBuffer.getChannelData(0);
    
    // Calculate RMS (Root Mean Square) for audio level
    let sum = 0;
    for (let i = 0; i < inputData.length; i++) {
      sum += inputData[i] * inputData[i];
    }
    const rms = Math.sqrt(sum / inputData.length);
    
    // Update audio level
    this.currentAudioLevel = rms;
    this.maxAudioLevel = Math.max(this.maxAudioLevel, rms);
    
    // Maintain audio level history
    this.audioLevelHistory.push(rms);
    if (this.audioLevelHistory.length > 100) { // Keep last 100 samples
      this.audioLevelHistory.shift();
    }
    
    // Voice activity detection
    if (this.config.enableVoiceActivityDetection) {
      this.updateVoiceActivity(rms);
    }
  }

  private updateVoiceActivity(audioLevel: number): void {
    // Add to voice activity buffer
    this.voiceActivityBuffer.push(audioLevel);
    if (this.voiceActivityBuffer.length > this.bufferSize) {
      this.voiceActivityBuffer.shift();
    }
    
    // Calculate average audio level
    const averageLevel = this.voiceActivityBuffer.reduce((a, b) => a + b, 0) / this.voiceActivityBuffer.length;
    
    // Determine voice activity
    const isVoiceDetected = averageLevel > this.voiceThreshold;
    const confidence = Math.min(averageLevel / this.voiceThreshold, 1.0);
    
    // Emit voice activity event
    const result: VoiceActivityResult = {
      isVoiceDetected,
      confidence,
      audioLevel: averageLevel,
      timestamp: Date.now()
    };
    
    // Call voice activity callback if available
    if ((window as any).onVoiceActivityDetected) {
      (window as any).onVoiceActivityDetected(result);
    }
  }

  getAudioLevel(): number {
    return this.currentAudioLevel;
  }

  getMaxAudioLevel(): number {
    return this.maxAudioLevel;
  }

  resetMaxAudioLevel(): void {
    this.maxAudioLevel = 0;
  }

  isVoiceActive(): boolean {
    return this.currentAudioLevel > this.voiceThreshold;
  }

  getAudioLevelHistory(): number[] {
    return [...this.audioLevelHistory];
  }

  setVoiceThreshold(threshold: number): void {
    this.voiceThreshold = Math.max(0, Math.min(1, threshold));
    (window as any).logBot?.(`[Audio Enhancement] Voice threshold set to: ${this.voiceThreshold}`);
  }

  setSilenceThreshold(threshold: number): void {
    this.silenceThreshold = Math.max(0, Math.min(1, threshold));
    (window as any).logBot?.(`[Audio Enhancement] Silence threshold set to: ${this.silenceThreshold}`);
  }

  setMicrophoneGain(gain: number): void {
    this.config.microphoneGain = Math.max(0, Math.min(2, gain));
    (window as any).logBot?.(`[Audio Enhancement] Microphone gain set to: ${this.config.microphoneGain}`);
    
    // Apply gain if nodes are available
    if (this.microphone && this.audioContext) {
      const gainNode = this.audioContext.createGain();
      gainNode.gain.value = this.config.microphoneGain;
      this.microphone.disconnect();
      this.microphone.connect(gainNode);
      if (this.analyser) {
        gainNode.connect(this.analyser);
      }
    }
  }

  // Enhanced audio quality metrics
  getAudioQualityMetrics(): {
    currentLevel: number;
    maxLevel: number;
    averageLevel: number;
    isClipping: boolean;
    noiseLevel: number;
    signalToNoiseRatio: number;
  } {
    const averageLevel = this.audioLevelHistory.length > 0 
      ? this.audioLevelHistory.reduce((a, b) => a + b, 0) / this.audioLevelHistory.length 
      : 0;
    
    // Estimate noise level from quietest 10% of samples
    const sortedLevels = [...this.audioLevelHistory].sort((a, b) => a - b);
    const noiseLevel = sortedLevels.length > 0 
      ? sortedLevels.slice(0, Math.max(1, Math.floor(sortedLevels.length * 0.1))).reduce((a, b) => a + b, 0) / Math.max(1, Math.floor(sortedLevels.length * 0.1))
      : 0;
    
    const signalToNoiseRatio = noiseLevel > 0 ? averageLevel / noiseLevel : 0;
    
    return {
      currentLevel: this.currentAudioLevel,
      maxLevel: this.maxAudioLevel,
      averageLevel,
      isClipping: this.maxAudioLevel > 0.95,
      noiseLevel,
      signalToNoiseRatio
    };
  }

  // Audio calibration
  async calibrateAudio(durationMs: number = 3000): Promise<{
    recommendedThreshold: number;
    noiseLevel: number;
    maxLevel: number;
  }> {
    (window as any).logBot?.('[Audio Enhancement] Starting audio calibration...');
    
    const calibrationData: number[] = [];
    const startTime = Date.now();
    
    return new Promise((resolve) => {
      const calibrationInterval = setInterval(() => {
        calibrationData.push(this.currentAudioLevel);
        
        if (Date.now() - startTime >= durationMs) {
          clearInterval(calibrationInterval);
          
          // Analyze calibration data
          const sortedData = [...calibrationData].sort((a, b) => a - b);
          const noiseLevel = sortedData.slice(0, Math.floor(sortedData.length * 0.3)).reduce((a, b) => a + b, 0) / Math.floor(sortedData.length * 0.3);
          const maxLevel = Math.max(...calibrationData);
          
          // Recommend threshold as 3x noise level
          const recommendedThreshold = Math.min(noiseLevel * 3, 0.1);
          
          this.setVoiceThreshold(recommendedThreshold);
          
          (window as any).logBot?.(`[Audio Enhancement] ✅ Calibration complete. Recommended threshold: ${recommendedThreshold}`);
          
          resolve({
            recommendedThreshold,
            noiseLevel,
            maxLevel
          });
        }
      }, 100);
    });
  }

  // Cleanup resources
  cleanup(): void {
    try {
      if (this.processor) {
        this.processor.disconnect();
        this.processor = null;
      }
      
      if (this.analyser) {
        this.analyser.disconnect();
        this.analyser = null;
      }
      
      if (this.microphone) {
        this.microphone.disconnect();
        this.microphone = null;
      }
      
      if (this.audioContext && this.audioContext.state !== 'closed') {
        this.audioContext.close();
        this.audioContext = null;
      }
      
      this.isInitialized = false;
      (window as any).logBot?.('[Audio Enhancement] Cleanup completed');
    } catch (error) {
      (window as any).logBot?.(`[Audio Enhancement] Cleanup error: ${error}`);
    }
  }

  isReady(): boolean {
    return this.isInitialized && this.audioContext !== null;
  }

  getConfiguration(): AudioConfig {
    return { ...this.config };
  }

  updateConfiguration(newConfig: Partial<AudioConfig>): void {
    this.config = { ...this.config, ...newConfig };
    (window as any).logBot?.('[Audio Enhancement] Configuration updated');
  }
}

// Audio visualization utilities
export class AudioVisualizer {
  private canvas: HTMLCanvasElement | null = null;
  private canvasContext: CanvasRenderingContext2D | null = null;
  private analyser: AnalyserNode | null = null;
  private animationFrame: number | null = null;

  constructor(canvasElement: HTMLCanvasElement, analyser: AnalyserNode) {
    this.canvas = canvasElement;
    this.canvasContext = canvasElement.getContext('2d');
    this.analyser = analyser;
  }

  startVisualization(): void {
    if (!this.canvas || !this.canvasContext || !this.analyser) return;

    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      this.animationFrame = requestAnimationFrame(draw);

      this.analyser!.getByteFrequencyData(dataArray);

      const canvasWidth = this.canvas!.width;
      const canvasHeight = this.canvas!.height;

      this.canvasContext!.fillStyle = 'rgb(0, 0, 0)';
      this.canvasContext!.fillRect(0, 0, canvasWidth, canvasHeight);

      const barWidth = (canvasWidth / bufferLength) * 2.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * canvasHeight;

        this.canvasContext!.fillStyle = `rgb(${barHeight + 100}, 50, 50)`;
        this.canvasContext!.fillRect(x, canvasHeight - barHeight / 2, barWidth, barHeight);

        x += barWidth + 1;
      }
    };

    draw();
  }

  stopVisualization(): void {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }
}

// Export global instance for easy access
export const audioEnhancementManager = new AudioEnhancementManager();


