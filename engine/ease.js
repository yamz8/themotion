// Easing curves. Each maps progress 0..1 to eased progress; springs and
// back curves overshoot 1 before settling.
themotion.ease = {
  linear: t => t,
  inCubic: t => t * t * t,
  outCubic: t => 1 - Math.pow(1 - t, 3),
  inOutCubic: t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
  outExpo: t => t >= 1 ? 1 : 1 - Math.pow(2, -10 * t),
  inOutExpo: t => t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2,
  // Overshoots by roughly 10% for s = 1.7; larger s overshoots more.
  outBack: (t, s = 1.70158) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2),
  // Damped spring: 0 at t = 0, rings around 1 and settles. damping and freq
  // are per unit of progress.
  spring: (t, damping = 5.2, freq = 9.5) => t <= 0 ? 0 : 1 - Math.exp(-damping * t) * Math.cos(freq * t),
  // A decaying wobble around 0 after an impact at t = 0 (t in seconds).
  wobble: (t, amount = 1, decay = 6, freq = 22) => t <= 0 ? 0 : amount * Math.exp(-t * decay) * Math.sin(t * freq),
}
