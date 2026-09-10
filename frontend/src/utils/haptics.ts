/**
 * Tactile Haptic & Audio Click Feedback Utility
 * Provides realistic physical button feel via Web Audio API micro-sounds and ripple shockwaves.
 */

let audioCtx: AudioContext | null = null;
let soundEnabled = true;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

export type ClickFeedbackType = "click" | "snap" | "pop" | "tab" | "chime";

/**
 * Play an ultra-short, satisfying mechanical switch micro-sound (10-25ms).
 * Simulates physical micro-switch tactile click feedback.
 */
export function playTactileClick(type: ClickFeedbackType = "click") {
  if (!soundEnabled) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    if (type === "click") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(1400, now);
      osc.frequency.exponentialRampToValueAtTime(120, now + 0.018);

      gain.gain.setValueAtTime(0.05, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.018);
      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.02);
    } else if (type === "snap") {
      osc.type = "triangle";
      osc.frequency.setValueAtTime(950, now);
      osc.frequency.exponentialRampToValueAtTime(90, now + 0.028);

      gain.gain.setValueAtTime(0.07, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.028);
      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.03);
    } else if (type === "tab") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(1900, now);
      osc.frequency.exponentialRampToValueAtTime(280, now + 0.022);

      gain.gain.setValueAtTime(0.06, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.022);
      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.025);
    } else if (type === "pop") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(540, now);
      osc.frequency.exponentialRampToValueAtTime(960, now + 0.025);

      gain.gain.setValueAtTime(0.05, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.025);
      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.03);
    } else if (type === "chime") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.exponentialRampToValueAtTime(1760, now + 0.06);

      gain.gain.setValueAtTime(0.04, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.06);
      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.065);
    }
  } catch {
    // Graceful no-op
  }
}

/**
 * Creates an electric cyan ripple shockwave on the clicked button.
 */
export function createClickRipple(e: React.SyntheticEvent | MouseEvent | Event) {
  const target = (e.currentTarget || e.target) as HTMLElement;
  const container = (target?.closest?.("button, a, .queue-filter-chip, [role='button']") as HTMLElement) || target;
  if (!container || typeof container.getBoundingClientRect !== "function") return;

  const rect = container.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height, 35) * 1.6;
  const mouseE = e as unknown as MouseEvent;
  const clientX = mouseE?.clientX != null ? mouseE.clientX : rect.left + rect.width / 2;
  const clientY = mouseE?.clientY != null ? mouseE.clientY : rect.top + rect.height / 2;
  const x = clientX - rect.left - size / 2;
  const y = clientY - rect.top - size / 2;

  const ripple = document.createElement("span");
  ripple.className = "click-ripple-wave";
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${x}px`;
  ripple.style.top = `${y}px`;

  if (window.getComputedStyle(container).position === "static") {
    container.style.position = "relative";
  }

  container.appendChild(ripple);

  setTimeout(() => {
    ripple.remove();
  }, 500);
}

/**
 * Universal tactile button feedback: Plays mechanical sound + triggers visual ripple
 */
export function triggerButtonFeedback(
  e?: React.SyntheticEvent | MouseEvent | Event,
  type: ClickFeedbackType = "click"
) {
  playTactileClick(type);
  if (e) {
    createClickRipple(e);
  }
}


export function isAudioEnabled(): boolean {
  return soundEnabled;
}

export function setAudioEnabled(enabled: boolean) {
  soundEnabled = enabled;
  if (enabled) playTactileClick("chime");
}

/**
 * Global initialization: automatically hooks into all button clicks and interactions
 */
export function initGlobalTactileFeedback() {
  if (typeof window === "undefined") return;

  // Auto-resume AudioContext on first user interaction
  const unlock = () => {
    getAudioContext();
  };
  window.addEventListener("pointerdown", unlock, { passive: true });
  window.addEventListener("keydown", unlock, { passive: true });

  // Universal click micro-feedback
  window.addEventListener("click", (e) => {
    const target = e.target as HTMLElement | null;
    const clickable = target?.closest("button, a, .queue-filter-chip, .row-action-icon-btn, .row-star-btn, [role='button']");
    if (clickable) {
      playTactileClick("click");
      createClickRipple(e);
    }
  }, { capture: true, passive: true });
}
