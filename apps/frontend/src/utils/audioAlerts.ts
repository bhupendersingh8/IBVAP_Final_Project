// Tactical Audio Alert Synthesizer using native Web Audio API
// No external sound assets or network requests required

let audioCtx: AudioContext | null = null;

const getAudioContext = (): AudioContext | null => {
  if (typeof window === 'undefined') return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
};

export const isAudioMuted = (): boolean => {
  if (typeof window === 'undefined') return true;
  return localStorage.getItem('ibvap_audio_muted') === 'true';
};

export const setAudioMuted = (muted: boolean): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('ibvap_audio_muted', muted ? 'true' : 'false');
};

/**
 * Plays an urgent two-tone pulsating perimeter breach alarm
 */
export const playBreachAlarm = () => {
  if (isAudioMuted()) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = 'sawtooth';
  // Modulate frequency between 880Hz and 600Hz
  osc.frequency.setValueAtTime(880, now);
  osc.frequency.linearRampToValueAtTime(600, now + 0.15);
  osc.frequency.linearRampToValueAtTime(880, now + 0.3);
  osc.frequency.linearRampToValueAtTime(600, now + 0.45);
  osc.frequency.linearRampToValueAtTime(880, now + 0.6);

  gain.gain.setValueAtTime(0.2, now);
  gain.gain.exponentialRampToValueAtTime(0.01, now + 0.65);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.7);
};

/**
 * Plays a double-pulse caution chime for medium alerts or simulated intrusions
 */
export const playWarningChime = () => {
  if (isAudioMuted()) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(587.33, now); // D5
  osc.frequency.setValueAtTime(783.99, now + 0.12); // G5

  gain.gain.setValueAtTime(0.15, now);
  gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.4);
};

/**
 * Plays a short crisp confirmation ping for successful actions
 */
export const playSuccessPing = () => {
  if (isAudioMuted()) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(1046.5, now); // C6

  gain.gain.setValueAtTime(0.15, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.25);
};
