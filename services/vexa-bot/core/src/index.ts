import StealthPlugin from "puppeteer-extra-plugin-stealth";
import { log } from "./utils";
import { chromium } from "playwright-extra";
import { handleGoogleMeet, leaveGoogleMeet } from "./platforms/google";
import { browserArgs, userAgent } from "./constans";
import { BotConfig, TTSAudioMessage, AudioSessionState } from "./types";
import { createClient, RedisClientType } from 'redis';
import { Page, Browser } from 'playwright-core';
import * as http from 'http'; // ADDED: For HTTP callback
import * as https from 'https'; // ADDED: For HTTPS callback (if needed)

// Module-level variables to store current configuration
let currentLanguage: string | null | undefined = null;
let currentTask: string | null | undefined = 'transcribe'; // Default task
let currentRedisUrl: string | null = null;
let currentConnectionId: string | null = null;
let botManagerCallbackUrl: string | null = null; // ADDED: To store callback URL
let currentPlatform: "google_meet" | "zoom" | "teams" | undefined;
let page: Page | null = null; // Initialize page, will be set in runBot

// --- ADDED: Flag to prevent multiple shutdowns ---
let isShuttingDown = false;
// ---------------------------------------------

// --- ADDED: Redis subscriber client ---
let redisSubscriber: RedisClientType | null = null;
// -----------------------------------

// --- ADDED: TTS Audio Consumer ---
let ttsAudioConsumer: RedisClientType | null = null;
let audioSessionState: AudioSessionState = {
  isPlaying: false,
  microphoneEnabled: false,
  currentAudioId: null,
  audioQueue: []
};

// --- ADDED: Session UID Tracking ---
let currentWhisperLiveSessionUID: string | null = null;
// ----------------------------------

// --- ADDED: Browser instance ---
let browserInstance: Browser | null = null;
// -------------------------------

// --- ADDED: Message Handler ---
// --- MODIFIED: Make async and add page parameter ---
const handleRedisMessage = async (message: string, channel: string, page: Page | null) => {
  // ++ ADDED: Log entry into handler ++
  log(`[DEBUG] handleRedisMessage entered for channel ${channel}. Message: ${message.substring(0, 100)}...`);
  // ++++++++++++++++++++++++++++++++++
  log(`Received command on ${channel}: ${message}`);
  // --- ADDED: Implement reconfigure command handling --- 
  try {
      const command = JSON.parse(message);
      if (command.action === 'reconfigure') {
          log(`Processing reconfigure command: Lang=${command.language}, Task=${command.task}`);

          // Update Node.js state
          currentLanguage = command.language;
          currentTask = command.task;

          // Trigger browser-side reconfiguration via the exposed function
          if (page && !page.isClosed()) { // Ensure page exists and is open
              try {
                  await page.evaluate(
                      ([lang, task]) => {
                          if (typeof (window as any).triggerWebSocketReconfigure === 'function') {
                              (window as any).triggerWebSocketReconfigure(lang, task);
                          } else {
                              console.error('[Node Eval Error] triggerWebSocketReconfigure not found on window.');
                              // Optionally log via exposed function if available
                              (window as any).logBot?.('[Node Eval Error] triggerWebSocketReconfigure not found on window.');
                          }
                      },
                      [currentLanguage, currentTask] // Pass new config as argument array
                  );
                  log("Sent reconfigure command to browser context via page.evaluate.");
              } catch (evalError: any) {
                  log(`Error evaluating reconfiguration script in browser: ${evalError.message}`);
              }
          } else {
               log("Page not available or closed, cannot send reconfigure command to browser.");
          }
      } else if (command.action === 'leave') {
        // TODO: Implement leave logic (Phase 4)
        log("Received leave command");
        if (!isShuttingDown && page && !page.isClosed()) { // Check flag and page state
          // A command-initiated leave is a successful completion, not an error.
          // Exit with code 0 to signal success to Nomad and prevent restarts.
          await performGracefulLeave(page, 0, "self_initiated_leave");
        } else {
           log("Ignoring leave command: Already shutting down or page unavailable.")
        }
      }
  } catch (e: any) {
      log(`Error processing Redis message: ${e.message}`);
  }
  // -------------------------------------------------
};
// ----------------------------

// --- ADDED: TTS Audio Message Handler ---
const handleTTSAudioMessage = async (message: string, channel: string, page: Page | null) => {
  log(`[TTS Audio] Received audio message on ${channel}: ${message.substring(0, 100)}...`);
  
  try {
    const audioData = JSON.parse(message);
    const ttsMessage: TTSAudioMessage = audioData.payload ? JSON.parse(audioData.payload) : audioData;
    
    // Enhanced session validation logic
    let sessionMatches = false;
    
    if (ttsMessage.session_uid) {
      // Primary: Match against WhisperLive session UID if available
      if (currentWhisperLiveSessionUID && ttsMessage.session_uid === currentWhisperLiveSessionUID) {
        sessionMatches = true;
        log(`[TTS Audio] Session matched via WhisperLive UID: ${ttsMessage.session_uid}`);
      }
      // Fallback: Match against connection ID for backward compatibility
      else if (currentConnectionId && ttsMessage.session_uid === currentConnectionId) {
        sessionMatches = true;
        log(`[TTS Audio] Session matched via connectionId fallback: ${ttsMessage.session_uid}`);
      }
      // If no match, log the mismatch details
      else {
        log(`[TTS Audio] Session mismatch - Message UID: ${ttsMessage.session_uid}, WhisperLive UID: ${currentWhisperLiveSessionUID}, ConnectionId: ${currentConnectionId}`);
      }
    } else {
      // If no session_uid in message, accept it (could be a broadcast message)
      sessionMatches = true;
      log(`[TTS Audio] No session_uid in message, accepting for processing`);
    }
    
    if (!sessionMatches) {
      log(`[TTS Audio] ❌ Audio message rejected - Session mismatch`);
      log(`[TTS Audio]   Message session_uid: ${ttsMessage.session_uid}`);
      log(`[TTS Audio]   Bot connectionId: ${currentConnectionId}`);
      log(`[TTS Audio]   WhisperLive UID: ${currentWhisperLiveSessionUID}`);
      log(`[TTS Audio]   Meeting ID in message: ${ttsMessage.meeting_id}`);
      return;
    }
    
    log(`[TTS Audio] ✅ Processing audio for question: "${ttsMessage.original_question}"`);
    log(`[TTS Audio] Response text: "${ttsMessage.response_text.substring(0, 50)}..."`);
    log(`[TTS Audio] Audio format: ${ttsMessage.audio_format}, Duration: ${ttsMessage.audio_duration}s`);
    
    // Validate required audio fields
    if (!ttsMessage.audio_data || !ttsMessage.message_id) {
      log(`[TTS Audio] ❌ Invalid audio message - missing audio_data or message_id`);
      return;
    }
    
    // Add to audio queue
    audioSessionState.audioQueue.push(ttsMessage);
    log(`[TTS Audio] Added to queue. Queue length: ${audioSessionState.audioQueue.length}`);
    
    // Process audio queue if not currently playing
    if (!audioSessionState.isPlaying && page && !page.isClosed()) {
      await processAudioQueue(page);
    }
    
  } catch (e: any) {
    log(`[TTS Audio] Error processing audio message: ${e.message}`);
  }
};

// --- ADDED: Audio Queue Processor ---
const processAudioQueue = async (page: Page) => {
  if (audioSessionState.isPlaying) {
    log(`[TTS Audio] Queue processor called but already playing audio: ${audioSessionState.currentAudioId}`);
    return;
  }
  
  if (audioSessionState.audioQueue.length === 0) {
    log(`[TTS Audio] Queue processor called but queue is empty`);
    return;
  }
  
  const audioMessage = audioSessionState.audioQueue.shift()!;
  audioSessionState.isPlaying = true;
  audioSessionState.currentAudioId = audioMessage.message_id;
  audioSessionState.playbackStartTime = Date.now();
  
  log(`[TTS Audio] 🎵 Starting playback of audio message: ${audioMessage.message_id}`);
  log(`[TTS Audio] Queue remaining: ${audioSessionState.audioQueue.length} messages`);
  
  try {
    // Send audio data to browser for playback
    await page.evaluate(
      (audioPayload: TTSAudioMessage) => {
        if (typeof (window as any).playTTSAudio === 'function') {
          (window as any).playTTSAudio(audioPayload);
        } else {
          console.error('[TTS Audio] playTTSAudio function not found on window');
          (window as any).logBot?.('[TTS Audio] playTTSAudio function not found on window');
        }
      },
      audioMessage
    );
    
    log(`[TTS Audio] ✅ Audio sent to browser for playback: ${audioMessage.message_id}`);
    
  } catch (evalError: any) {
    log(`[TTS Audio] ❌ Error sending audio to browser: ${evalError.message}`);
    // Reset state on error
    audioSessionState.isPlaying = false;
    audioSessionState.currentAudioId = null;
    // Process next in queue
    if (audioSessionState.audioQueue.length > 0) {
      log(`[TTS Audio] Retrying queue processing in 1 second...`);
      setTimeout(() => processAudioQueue(page), 1000);
    }
  }
};

// --- ADDED: Audio Playback Completion Handler ---
const handleAudioPlaybackComplete = async (audioId: string, page: Page) => {
  log(`[TTS Audio] 🎵 Audio playback completed: ${audioId}`);
  
  if (audioSessionState.currentAudioId === audioId) {
    const playbackDuration = audioSessionState.playbackStartTime ? Date.now() - audioSessionState.playbackStartTime : 0;
    log(`[TTS Audio] Playback duration: ${playbackDuration}ms`);
    
    audioSessionState.isPlaying = false;
    audioSessionState.currentAudioId = null;
    audioSessionState.playbackStartTime = undefined;
    
    // Process next audio in queue
    if (audioSessionState.audioQueue.length > 0) {
      log(`[TTS Audio] Processing next audio in queue (${audioSessionState.audioQueue.length} remaining)`);
      setTimeout(() => processAudioQueue(page), 500); // Small delay before next audio
    } else {
      log(`[TTS Audio] Audio queue is now empty`);
    }
  } else {
    log(`[TTS Audio] ⚠️  Completion notification for ${audioId}, but current audio is ${audioSessionState.currentAudioId}`);
  }
};
// ----------------------------------------

// --- ADDED: Graceful Leave Function ---
async function performGracefulLeave(
  page: Page | null, // Allow page to be null for cases where it might not be available
  exitCode: number = 1, // Default to 1 (failure/generic error)
  reason: string = "self_initiated_leave", // Default reason
  errorDetails?: any // Optional detailed error information
): Promise<void> {
  if (isShuttingDown) {
    log("[Graceful Leave] Already in progress, ignoring duplicate call.");
    return;
  }
  isShuttingDown = true;
  log(`[Graceful Leave] Initiating graceful shutdown sequence... Reason: ${reason}, Exit Code: ${exitCode}`);

  let platformLeaveSuccess = false;
  if (page && !page.isClosed()) { // Only attempt platform leave if page is valid
    try {
      log("[Graceful Leave] Attempting platform-specific leave...");
      // Assuming currentPlatform is set appropriately, or determine it if needed
      if (currentPlatform === "google_meet") { // Add platform check if you have other platform handlers
         platformLeaveSuccess = await leaveGoogleMeet(page);
      } else {
         log(`[Graceful Leave] No platform-specific leave defined for ${currentPlatform}. Page will be closed.`);
         // If no specific leave, we still consider it "handled" to proceed with cleanup.
         // The exitCode passed to this function will determine the callback's exitCode.
         platformLeaveSuccess = true; // Or false if page closure itself is the "action"
      }
      log(`[Graceful Leave] Platform leave/close attempt result: ${platformLeaveSuccess}`);
    } catch (leaveError: any) {
      log(`[Graceful Leave] Error during platform leave/close attempt: ${leaveError.message}`);
      platformLeaveSuccess = false;
    }
  } else {
    log("[Graceful Leave] Page not available or already closed. Skipping platform-specific leave attempt.");
    // If the page is already gone, we can't perform a UI leave.
    // The provided exitCode and reason will dictate the callback.
    // If reason is 'admission_failed', exitCode would be 2, and platformLeaveSuccess is irrelevant.
  }

  // Determine final exit code. If the initial intent was a successful exit (code 0),
  // it should always be 0. For error cases (non-zero exit codes), preserve the original error code.
  const finalCallbackExitCode = (exitCode === 0) ? 0 : exitCode;
  const finalCallbackReason = reason;

  if (botManagerCallbackUrl && currentConnectionId) {
    const payload = JSON.stringify({
      connection_id: currentConnectionId,
      exit_code: finalCallbackExitCode,
      reason: finalCallbackReason,
      error_details: errorDetails || null,
      platform_specific_error: errorDetails?.error_message || null
    });

    try {
      log(`[Graceful Leave] Sending exit callback to ${botManagerCallbackUrl} with payload: ${payload}`);
      const url = new URL(botManagerCallbackUrl);
      const options: https.RequestOptions = { // Added type
        method: 'POST',
        hostname: url.hostname,
        port: url.port || (url.protocol === 'https:' ? '443' : '80'),
        path: url.pathname,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload) // Assumes Buffer is available
        }
      };

      const req = (url.protocol === 'https:' ? https : http).request(options, (res: http.IncomingMessage) => { // Added type
        log(`[Graceful Leave] Bot-manager callback response status: ${res.statusCode}`);
        res.on('data', () => { /* consume data */ });
      });

      req.on('error', (err: Error) => { // Added type
        log(`[Graceful Leave] Error sending bot-manager callback: ${err.message}`);
      });

      req.write(payload);
      req.end();
      await new Promise(resolve => setTimeout(resolve, 500)); 
    } catch (callbackError: any) {
      log(`[Graceful Leave] Exception during bot-manager callback preparation: ${callbackError.message}`);
    }
  } else {
    log("[Graceful Leave] Bot manager callback URL or Connection ID not configured. Cannot send exit status.");
  }

  if (redisSubscriber && redisSubscriber.isOpen) {
    log("[Graceful Leave] Disconnecting Redis subscriber...");
    try {
        await redisSubscriber.unsubscribe();
        await redisSubscriber.quit();
        log("[Graceful Leave] Redis subscriber disconnected.");
    } catch (err) {
        log(`[Graceful Leave] Error closing Redis connection: ${err}`);
    }
  }

  // --- ADDED: Close TTS Audio Consumer ---
  if (ttsAudioConsumer && ttsAudioConsumer.isOpen) {
    log("[Graceful Leave] Disconnecting TTS Audio consumer...");
    try {
        await ttsAudioConsumer.unsubscribe();
        await ttsAudioConsumer.quit();
        log("[Graceful Leave] TTS Audio consumer disconnected.");
    } catch (err) {
        log(`[Graceful Leave] Error closing TTS Audio Redis connection: ${err}`);
    }
  }
  // ------------------------------------------

  // Close the browser page if it's still open and wasn't closed by platform leave
  if (page && !page.isClosed()) {
    log("[Graceful Leave] Ensuring page is closed.");
    try {
      await page.close();
      log("[Graceful Leave] Page closed.");
    } catch (pageCloseError: any) {
      log(`[Graceful Leave] Error closing page: ${pageCloseError.message}`);
    }
  }

  // Close the browser instance
  log("[Graceful Leave] Closing browser instance...");
  try {
    if (browserInstance && browserInstance.isConnected()) {
       await browserInstance.close();
       log("[Graceful Leave] Browser instance closed.");
    } else {
       log("[Graceful Leave] Browser instance already closed or not available.");
    }
  } catch (browserCloseError: any) {
    log(`[Graceful Leave] Error closing browser: ${browserCloseError.message}`);
  }

  // Exit the process
  // The process exit code should reflect the overall success/failure.
  // If callback used finalCallbackExitCode, process.exit could use the same.
  log(`[Graceful Leave] Exiting process with code ${finalCallbackExitCode} (Reason: ${finalCallbackReason}).`);
  process.exit(finalCallbackExitCode);
}
// --- ----------------------------- ---

// --- ADDED: Function to be called from browser to trigger leave ---
// This needs to be defined in a scope where 'page' will be available when it's exposed.
// We will define the actual exposed function inside runBot where 'page' is in scope.
// --- ------------------------------------------------------------ ---

export async function runBot(botConfig: BotConfig): Promise<void> {
  // --- UPDATED: Parse and store config values ---
  currentLanguage = botConfig.language;
  currentTask = botConfig.task || 'transcribe';
  currentRedisUrl = botConfig.redisUrl;
  currentConnectionId = botConfig.connectionId;
  botManagerCallbackUrl = botConfig.botManagerCallbackUrl || null; // ADDED: Get callback URL from botConfig
  currentPlatform = botConfig.platform; // Set currentPlatform here

  // Destructure other needed config values
  const { meetingUrl, platform, botName } = botConfig;

  log(`Starting bot for ${platform} with URL: ${meetingUrl}, name: ${botName}, language: ${currentLanguage}, task: ${currentTask}, connectionId: ${currentConnectionId}`);

  // --- ADDED: Redis Client Setup and Subscription ---
  if (currentRedisUrl && currentConnectionId) {
    log("Setting up Redis subscriber...");
    try {
      redisSubscriber = createClient({ url: currentRedisUrl });

      redisSubscriber.on('error', (err) => log(`Redis Client Error: ${err}`));
      // ++ ADDED: Log connection events ++
      redisSubscriber.on('connect', () => log('[DEBUG] Redis client connecting...'));
      redisSubscriber.on('ready', () => log('[DEBUG] Redis client ready.'));
      redisSubscriber.on('reconnecting', () => log('[DEBUG] Redis client reconnecting...'));
      redisSubscriber.on('end', () => log('[DEBUG] Redis client connection ended.'));
      // ++++++++++++++++++++++++++++++++++

      await redisSubscriber.connect();
      log(`Connected to Redis at ${currentRedisUrl}`);

      const commandChannel = `bot_commands:${currentConnectionId}`;
      // Pass the page object when subscribing
      // ++ MODIFIED: Add logging inside subscribe callback ++
      await redisSubscriber.subscribe(commandChannel, (message, channel) => {
          log(`[DEBUG] Redis subscribe callback fired for channel ${channel}.`); // Log before handling
          handleRedisMessage(message, channel, page)
      }); 
      // ++++++++++++++++++++++++++++++++++++++++++++++++
      log(`Subscribed to Redis channel: ${commandChannel}`);

      // --- ADDED: Setup TTS Audio Consumer ---
      log("Setting up TTS audio consumer...");
      try {
        ttsAudioConsumer = createClient({ url: currentRedisUrl });
        
        ttsAudioConsumer.on('error', (err) => log(`TTS Audio Redis Client Error: ${err}`));
        ttsAudioConsumer.on('connect', () => log('[DEBUG] TTS Audio Redis client connecting...'));
        ttsAudioConsumer.on('ready', () => log('[DEBUG] TTS Audio Redis client ready.'));
        ttsAudioConsumer.on('reconnecting', () => log('[DEBUG] TTS Audio Redis client reconnecting...'));
        ttsAudioConsumer.on('end', () => log('[DEBUG] TTS Audio Redis client connection ended.'));

        await ttsAudioConsumer.connect();
        log(`TTS Audio Consumer connected to Redis at ${currentRedisUrl}`);

        const ttsAudioChannel = process.env.TTS_AUDIO_STREAM_NAME || 'tts_audio_queue';
        await ttsAudioConsumer.subscribe(ttsAudioChannel, (message, channel) => {
          log(`[DEBUG] TTS Audio subscribe callback fired for channel ${channel}.`);
          handleTTSAudioMessage(message, channel, page);
        });
        log(`TTS Audio Consumer subscribed to Redis channel: ${ttsAudioChannel}`);

      } catch (ttsErr) {
        log(`*** Failed to setup TTS Audio Consumer: ${ttsErr} ***`);
        ttsAudioConsumer = null;
      }
      // ----------------------------------------

    } catch (err) {
      log(`*** Failed to connect or subscribe to Redis: ${err} ***`);
      // Decide how to handle this - exit? proceed without command support?
      // For now, log the error and proceed without Redis.
      redisSubscriber = null; // Ensure client is null if setup failed
    }
  } else {
    log("Redis URL or Connection ID missing, skipping Redis setup.");
  }
  // -------------------------------------------------

  // Use Stealth Plugin to avoid detection
  const stealthPlugin = StealthPlugin();
  stealthPlugin.enabledEvasions.delete("iframe.contentWindow");
  stealthPlugin.enabledEvasions.delete("media.codecs");
  chromium.use(stealthPlugin);

  // Launch browser with stealth configuration
  browserInstance = await chromium.launch({
    headless: false,
    args: browserArgs,
  });

  // Create a new page with permissions and viewport
  const context = await browserInstance.newContext({
    permissions: ["camera", "microphone"],
    userAgent: userAgent,
    viewport: {
      width: 1280,
      height: 720
    }
  })
  page = await context.newPage(); // Assign to the module-scoped page variable

  // --- ADDED: Expose a function for browser to trigger Node.js graceful leave ---
  await page.exposeFunction("triggerNodeGracefulLeave", async () => {
    log("[Node.js] Received triggerNodeGracefulLeave from browser context.");
    if (!isShuttingDown) {
      await performGracefulLeave(page, 0, "self_initiated_leave_from_browser");
    } else {
      log("[Node.js] Ignoring triggerNodeGracefulLeave as shutdown is already in progress.");
    }
  });
  
  // --- ADDED: Expose audio completion handler ---
  await page.exposeFunction("notifyAudioPlaybackComplete", async (audioId: string) => {
    log(`[Node.js] Received audio playback completion notification: ${audioId}`);
    if (page) {
      await handleAudioPlaybackComplete(audioId, page);
    } else {
      log(`[Node.js] Warning: Page is null, cannot handle audio completion`);
    }
  });
  
  // --- ADDED: Expose session UID update handler ---
  await page.exposeFunction("updateWhisperLiveSessionUID", async (sessionUID: string) => {
    log(`[Node.js] Updating WhisperLive session UID: ${sessionUID}`);
    currentWhisperLiveSessionUID = sessionUID;
    log(`[Session Tracking] Bot ConnectionId: ${currentConnectionId}, WhisperLive UID: ${currentWhisperLiveSessionUID}`);
  });
  // --- ----------------------------------------------------------------------- ---

  // Setup anti-detection measures
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    Object.defineProperty(navigator, "plugins", {
      get: () => [{ name: "Chrome PDF Plugin" }, { name: "Chrome PDF Viewer" }],
    });
    Object.defineProperty(navigator, "languages", {
      get: () => ["en-US", "en"],
    });
    Object.defineProperty(navigator, "hardwareConcurrency", { get: () => 4 });
    Object.defineProperty(navigator, "deviceMemory", { get: () => 8 });
    Object.defineProperty(window, "innerWidth", { get: () => 1920 });
    Object.defineProperty(window, "innerHeight", { get: () => 1080 });
    Object.defineProperty(window, "outerWidth", { get: () => 1920 });
    Object.defineProperty(window, "outerHeight", { get: () => 1080 });
  });

  // Call the appropriate platform handler
  try {
    if (botConfig.platform === "google_meet") {
      await handleGoogleMeet(botConfig, page, performGracefulLeave);
    } else if (botConfig.platform === "zoom") {
      log("Zoom platform not yet implemented.");
      await performGracefulLeave(page, 1, "platform_not_implemented");
    } else if (botConfig.platform === "teams") {
      log("Teams platform not yet implemented.");
      await performGracefulLeave(page, 1, "platform_not_implemented");
    } else {
      log(`Unknown platform: ${botConfig.platform}`);
      await performGracefulLeave(page, 1, "unknown_platform");
    }
  } catch (error: any) {
    log(`Error during platform handling: ${error.message}`);
    await performGracefulLeave(page, 1, "platform_handler_exception");
  }

  // If we reached here without an explicit shutdown (e.g., admission failed path returned, or normal end),
  // force a graceful exit to ensure the container terminates cleanly.
  await performGracefulLeave(page, 0, "normal_completion");
}

// --- ADDED: Basic Signal Handling (for future Phase 5) ---
// Setup signal handling to also trigger graceful leave
const gracefulShutdown = async (signal: string) => {
    log(`Received signal: ${signal}. Triggering graceful shutdown.`);
    if (!isShuttingDown) {
        // Determine the correct page instance if multiple are possible, or use a global 'currentPage'
        // For now, assuming 'page' (if defined globally/module-scoped) or null
        const pageToClose = typeof page !== 'undefined' ? page : null;
        await performGracefulLeave(pageToClose, signal === 'SIGINT' ? 130 : 143, `signal_${signal.toLowerCase()}`);
    } else {
         log("[Signal Shutdown] Shutdown already in progress.");
    }
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
// --- ------------------------------------------------- ---
