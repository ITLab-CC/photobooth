// Short sounds made with the Web Audio API, so no audio files are needed and it works offline.
// Browsers only allow sound after a touch; the countdown starts from one, so that is always the case.

let context: AudioContext | null = null;

const audio = (): AudioContext | null => {
  try {
    context = context ?? new AudioContext();
    if (context.state === "suspended") {
      void context.resume();
    }
    return context;
  } catch {
    return null; // no audio device: stay silent
  }
};

const tone = (frequency: number, seconds: number, volume: number, type: OscillatorType = "sine") => {
  const ctx = audio();
  if (!ctx) return;
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = type;
  oscillator.frequency.value = frequency;
  const now = ctx.currentTime;
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(volume, now + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + seconds);
  oscillator.connect(gain).connect(ctx.destination);
  oscillator.start(now);
  oscillator.stop(now + seconds + 0.02);
};

/** One tick of the countdown (3, 2, 1). */
export const playTick = () => tone(660, 0.14, 0.35);

/** The higher tone on "Los!". */
export const playGo = () => tone(990, 0.3, 0.4);

/** A short camera-shutter click: a burst of noise. */
export const playShutter = () => {
  const ctx = audio();
  if (!ctx) return;
  const length = Math.floor(ctx.sampleRate * 0.09);
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) {
    data[i] = (Math.random() * 2 - 1) * (1 - i / length);
  }
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  const filter = ctx.createBiquadFilter();
  filter.type = "bandpass";
  filter.frequency.value = 2200;
  const gain = ctx.createGain();
  gain.gain.value = 0.7;
  source.connect(filter).connect(gain).connect(ctx.destination);
  source.start();
};

/** A soft two-note chime between the photos of a series. */
export const playChime = () => {
  tone(784, 0.18, 0.25);
  setTimeout(() => tone(1047, 0.25, 0.25), 140);
};
