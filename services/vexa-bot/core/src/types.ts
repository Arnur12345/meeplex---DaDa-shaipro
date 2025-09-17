export type BotConfig = {
  platform: "google_meet" | "zoom" | "teams",
  meetingUrl: string | null,
  botName: string,
  token: string,
  connectionId: string,
  nativeMeetingId: string,
  language?: string | null,
  task?: string | null,
  redisUrl: string,
  container_name?: string,
  automaticLeave: {
    waitingRoomTimeout: number,
    noOneJoinedTimeout: number,
    everyoneLeftTimeout: number
  },
  reconnectionIntervalMs?: number,
  meeting_id?: number,
  botManagerCallbackUrl?: string;
}

// ADDED: TTS Audio Message Types
export type TTSAudioMessage = {
  audio_data: string; // Base64 encoded audio
  audio_metadata: {
    format: string;
    duration_seconds?: number;
    size_bytes?: number;
    engine?: string;
  };
  session_uid: string;
  meeting_id: string;
  original_question: string;
  response_text: string;
  audio_format: string;
  audio_duration?: number;
  audio_size?: number;
  tts_engine?: string;
  timestamp: string;
  original_timestamp?: string;
  message_id: string;
}

// ADDED: Audio Session State Types
export type AudioSessionState = {
  isPlaying: boolean;
  microphoneEnabled: boolean;
  currentAudioId: string | null;
  playbackStartTime?: number;
  audioQueue: TTSAudioMessage[];
}
