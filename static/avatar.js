/**
 * Raygent Advanced Multi-Pose & Living Avatar Engine
 * - Dynamic 6 photorealistic poses with smooth cross-fade morphing
 * - Organic breathing, shoulder swaying, and posture shifts
 * - Natural random eye micro-blinking & thoughtful head tilts
 * - Real-time frequency-reactive mouth viseme synthesis
 * - Audio-reactive energy particle aura & neon waveform ring
 * - Synchronized video avatar loop support
 */
class RaygentAvatarEngine {
  constructor() {
    this.videoEl = document.getElementById('avatar-video');
    this.canvasEl = document.getElementById('avatar-portrait-canvas');
    this.canvasCtx = this.canvasEl.getContext('2d');
    this.visualizerCanvas = document.getElementById('visualizer-canvas');
    this.visCtx = this.visualizerCanvas.getContext('2d');
    this.frameEl = document.getElementById('avatar-frame');
    this.statusPill = document.getElementById('agent-status-pill');
    this.statusLabel = document.getElementById('status-label');

    this.currentMode = 'image'; // 'image' or 'video'
    this.currentStatus = 'idle'; // 'idle', 'listening', 'thinking', 'speaking'
    this.activePose = 'idle';
    this.prevPose = 'idle';
    this.transitionProgress = 1.0; // 0.0 to 1.0

    // 6 Poses Image Cache
    this.poseUrls = {
      'idle': '/static/avatars/ray_idle.png',
      'yes': '/static/avatars/ray_yes.jpg',
      'no': '/static/avatars/ray_no.jpg',
      'whats_it_to_you': '/static/avatars/ray_whats_it_to_you.jpg',
      'let_me_check': '/static/avatars/ray_let_me_check.jpg',
      'without_me': '/static/avatars/ray_without_me.jpg'
    };

    this.poseImages = {};
    this.loadedPoses = new Set();
    this.preloadPoses();

    // Natural Blinking State
    this.lastBlinkTime = performance.now();
    this.nextBlinkInterval = 4000;
    this.blinkDuration = 140; // ms
    this.isBlinking = false;

    // Orbiting Aura Particles
    this.particles = [];
    this.initParticles(24);

    // Audio Analysis & Viseme mouth control
    this.audioCtx = null;
    this.analyser = null;
    this.dataArray = null;
    this.mouthOpen = 0; // 0 to 1
    this.speechEnergy = 0;
    this.lastFrameTime = performance.now();
    this.currentSourceNode = null;
    this.currentAudio = null;
    this.isAudioPlaying = false;
    this.mouthInterval = null;

    this.initVisualizer();
    this.initAudioUnlock();
    this.renderLoop();
  }

  preloadPoses() {
    for (const [name, url] of Object.entries(this.poseUrls)) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = url;
      img.onload = () => {
        this.loadedPoses.add(name);
        if (name === this.activePose) {
          this.canvasEl.classList.add('active');
          this.videoEl.classList.remove('active');
        }
      };
      this.poseImages[name] = img;
    }
  }

  initVisualizer() {
    try {
      window.AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContext();
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 64;
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    } catch (e) {}
  }

  initAudioUnlock() {
    const unlock = () => {
      if (this.audioCtx && this.audioCtx.state === 'suspended') {
        this.audioCtx.resume().catch(() => {});
      }
    };
    ['click', 'touchstart', 'keydown'].forEach(evt => {
      window.addEventListener(evt, unlock, { passive: true });
    });
  }

  initParticles(count) {
    this.particles = [];
    for (let i = 0; i < count; i++) {
      this.particles.push({
        angle: Math.random() * Math.PI * 2,
        speed: 0.008 + Math.random() * 0.018,
        radiusOffset: (Math.random() - 0.5) * 20,
        size: 1.5 + Math.random() * 2.5,
        alpha: 0.2 + Math.random() * 0.6,
        pulseSpeed: 1 + Math.random() * 2
      });
    }
  }

  setPose(poseName) {
    if (!poseName) return;
    poseName = poseName.toLowerCase();
    if (this.poseUrls[poseName] && poseName !== this.activePose) {
      this.prevPose = this.activePose;
      this.activePose = poseName;
      this.transitionProgress = 0.0; // trigger smooth cross-fade
      this.currentMode = 'image';
      this.videoEl.classList.remove('active');
      this.canvasEl.classList.add('active');

      // Update manual buttons active state
      document.querySelectorAll('.pose-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-pose') === poseName);
      });
    }
  }

  setAvatarSource(url, type) {
    this.currentMode = type;
    if (type === 'video') {
      this.videoEl.classList.add('active');
      this.canvasEl.classList.remove('active');
      this.videoEl.src = url;
      this.videoEl.play().catch(() => {});
    } else {
      this.videoEl.classList.remove('active');
      this.canvasEl.classList.add('active');
      const customImg = new Image();
      customImg.src = url;
      customImg.onload = () => {
        this.poseImages['custom'] = customImg;
        this.prevPose = this.activePose;
        this.activePose = 'custom';
        this.transitionProgress = 0.0;
      };
    }
  }

  setStatus(status) {
    if (status === 'idle' && this.isAudioPlaying) {
      return; // Keep speaking state while voice audio is still playing
    }
    this.currentStatus = status;
    if (this.statusLabel) this.statusLabel.textContent = status.toUpperCase();
    if (this.statusPill) this.statusPill.className = `status-pill ${status}`;
    if (this.frameEl) this.frameEl.className = `avatar-frame ${status}`;

    if (this.currentMode === 'video') {
      if (status === 'speaking') {
        this.videoEl.playbackRate = 1.15;
      } else if (status === 'thinking') {
        this.videoEl.playbackRate = 0.75;
      } else {
        this.videoEl.playbackRate = 1.0;
      }
    }
  }

  stopAudio() {
    if (this.mouthInterval) {
      clearInterval(this.mouthInterval);
      this.mouthInterval = null;
    }
    if (this.currentSourceNode) {
      try {
        this.currentSourceNode.stop();
        this.currentSourceNode.disconnect();
      } catch (e) {}
      this.currentSourceNode = null;
    }
    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.src = '';
      } catch (e) {}
      this.currentAudio = null;
    }
    this.isAudioPlaying = false;
    this.mouthOpen = 0;
    this.speechEnergy = 0;
  }

  async playAudioUrl(url) {
    if (!url) return;
    this.stopAudio();
    this.isAudioPlaying = true;
    this.setStatus('speaking');

    // Ensure AudioContext is running
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      try {
        await this.audioCtx.resume();
      } catch (e) {}
    }

    let playedViaWebAudio = false;
    if (this.audioCtx && this.analyser) {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);

        const source = this.audioCtx.createBufferSource();
        source.buffer = audioBuffer;

        // Connect source -> analyser -> destination
        source.connect(this.analyser);
        this.analyser.connect(this.audioCtx.destination);
        this.currentSourceNode = source;

        source.onended = () => {
          this.isAudioPlaying = false;
          this.mouthOpen = 0;
          this.speechEnergy = 0;
          this.setStatus('idle');
          this.currentSourceNode = null;
        };

        source.start(0);
        playedViaWebAudio = true;
      } catch (err) {
        console.warn("[AvatarEngine] Web Audio Buffer playback fallback to HTML5 Audio:", err);
      }
    }

    // Fail-safe fallback: direct HTML5 Audio element directly through browser media pipeline
    if (!playedViaWebAudio) {
      try {
        const audio = new Audio();
        audio.crossOrigin = 'anonymous';
        audio.src = url;
        this.currentAudio = audio;

        // Dynamic mouth flapping cadence while audio is playing
        this.mouthInterval = setInterval(() => {
          if (!this.isAudioPlaying) {
            clearInterval(this.mouthInterval);
            this.mouthInterval = null;
            return;
          }
          this.mouthOpen = 0.25 + Math.random() * 0.65;
          this.speechEnergy = 0.3 + Math.random() * 0.45;
        }, 85);

        audio.onended = () => {
          if (this.mouthInterval) {
            clearInterval(this.mouthInterval);
            this.mouthInterval = null;
          }
          this.isAudioPlaying = false;
          this.mouthOpen = 0;
          this.speechEnergy = 0;
          this.setStatus('idle');
          this.currentAudio = null;
        };

        audio.onerror = (e) => {
          console.error("[AvatarEngine] HTML5 Audio error:", e);
          if (this.mouthInterval) {
            clearInterval(this.mouthInterval);
            this.mouthInterval = null;
          }
          this.isAudioPlaying = false;
          this.setStatus('idle');
          this.currentAudio = null;
        };

        await audio.play();
      } catch (playErr) {
        console.error("[AvatarEngine] Failed to play audio through HTML5 Audio:", playErr);
        if (this.mouthInterval) {
          clearInterval(this.mouthInterval);
          this.mouthInterval = null;
        }
        this.isAudioPlaying = false;
        this.setStatus('idle');
      }
    }
  }

  setMouthAperture(value) {
    this.mouthOpen = Math.min(1.0, Math.max(0.0, value));
  }

  renderLoop() {
    requestAnimationFrame(() => this.renderLoop());

    const now = performance.now();
    const dt = Math.min(0.1, (now - this.lastFrameTime) / 1000);
    this.lastFrameTime = now;

    // Advance pose transition progress
    if (this.transitionProgress < 1.0) {
      this.transitionProgress = Math.min(1.0, this.transitionProgress + dt * 4.5); // ~220ms blend
    }

    // Check blinking
    this.updateBlinking(now);

    // Audio energy extraction
    this.updateAudioEnergy();

    this.drawVisualizer(now);

    if (this.currentMode === 'image') {
      this.drawPoseCanvas(now);
    }
  }

  updateBlinking(now) {
    if (!this.isBlinking) {
      if (now - this.lastBlinkTime > this.nextBlinkInterval) {
        this.isBlinking = true;
        this.blinkStartTime = now;
      }
    } else {
      if (now - this.blinkStartTime > this.blinkDuration) {
        this.isBlinking = false;
        this.lastBlinkTime = now;
        this.nextBlinkInterval = 3200 + Math.random() * 3000; // 3.2 to 6.2s
      }
    }
  }

  updateAudioEnergy() {
    if (this.analyser && this.dataArray && this.isAudioPlaying) {
      this.analyser.getByteFrequencyData(this.dataArray);
      const len = this.dataArray.length;
      
      // Multi-band Formant Spectral Energy
      let lowSum = 0, midSum = 0, highSum = 0;
      const lowCut = Math.floor(len * 0.25);
      const midCut = Math.floor(len * 0.65);
      
      for (let i = 0; i < len; i++) {
        const val = this.dataArray[i];
        if (i < lowCut) lowSum += val;
        else if (i < midCut) midSum += val;
        else highSum += val;
      }
      
      const lowEnergy = (lowSum / (lowCut || 1)) / 255;
      const midEnergy = (midSum / ((midCut - lowCut) || 1)) / 255;
      const highEnergy = (highSum / ((len - midCut) || 1)) / 255;
      const rawTotal = (lowEnergy + midEnergy + highEnergy) / 3;

      // Smooth attack/decay interpolation
      this.speechEnergy = this.speechEnergy * 0.75 + rawTotal * 0.25;
      this.visemeJaw = Math.min(1.0, lowEnergy * 3.6);
      this.visemeSpread = Math.min(1.0, midEnergy * 3.2);
      this.visemeSibilant = Math.min(1.0, highEnergy * 2.8);
      this.mouthOpen = this.mouthOpen * 0.7 + Math.max(this.visemeJaw, this.visemeSpread * 0.6) * 0.3;
    } else if (this.currentStatus === 'speaking') {
      this.speechEnergy = this.speechEnergy || 0.35;
      this.visemeJaw = 0.35;
      this.visemeSpread = 0.4;
      this.visemeSibilant = 0.2;
    } else {
      this.speechEnergy = 0;
      this.mouthOpen = 0;
      this.visemeJaw = 0;
      this.visemeSpread = 0;
      this.visemeSibilant = 0;
    }
  }

  drawVisualizer(now) {
    const ctx = this.visCtx;
    const w = this.visualizerCanvas.width;
    const h = this.visualizerCanvas.height;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const baseRadius = 96;

    let energy = this.speechEnergy;
    if (this.currentStatus === 'speaking' && energy < 0.15) {
      energy = 0.25 + Math.sin(now * 0.01) * 0.15;
    }

    let primaryColor = '#00f0ff';
    let secondaryColor = '#ff007f';
    if (this.currentStatus === 'speaking') {
      primaryColor = '#ff007f';
      secondaryColor = '#00f0ff';
    } else if (this.currentStatus === 'thinking') {
      primaryColor = '#7928ca';
      secondaryColor = '#ff007f';
    } else if (this.currentStatus === 'listening') {
      primaryColor = '#ffb703';
      secondaryColor = '#00f0ff';
    }

    // Outer Pulsing Aura Ring
    ctx.save();
    ctx.beginPath();
    const dynamicRadius = baseRadius + 8 + (energy * 24);
    ctx.arc(cx, cy, dynamicRadius, 0, Math.PI * 2);
    ctx.strokeStyle = primaryColor;
    ctx.lineWidth = 2 + (energy * 4);
    ctx.shadowColor = primaryColor;
    ctx.shadowBlur = 16 + (energy * 20);
    ctx.stroke();
    ctx.restore();

    // Audio Frequency Spikes
    if (this.dataArray) {
      const bars = 40;
      for (let i = 0; i < bars; i++) {
        const val = this.dataArray[i % this.dataArray.length] || 0;
        const barHeight = (val / 255) * (20 + energy * 25);
        const angle = (i / bars) * Math.PI * 2;

        const x1 = cx + Math.cos(angle) * (baseRadius + 2);
        const y1 = cy + Math.sin(angle) * (baseRadius + 2);
        const x2 = cx + Math.cos(angle) * (baseRadius + 2 + barHeight);
        const y2 = cy + Math.sin(angle) * (baseRadius + 2 + barHeight);

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = (i % 2 === 0) ? primaryColor : secondaryColor;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    // Orbiting Floating Energy Particles
    for (const p of this.particles) {
      p.angle += p.speed * (1 + energy * 2);
      const pr = baseRadius + 14 + p.radiusOffset + Math.sin(now * 0.003 * p.pulseSpeed) * 6;
      const px = cx + Math.cos(p.angle) * pr;
      const py = cy + Math.sin(p.angle) * pr;

      ctx.save();
      ctx.beginPath();
      ctx.arc(px, py, p.size * (1 + energy * 0.8), 0, Math.PI * 2);
      ctx.fillStyle = primaryColor;
      ctx.globalAlpha = p.alpha;
      ctx.shadowColor = primaryColor;
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.restore();
    }
  }

  drawPoseCanvas(now) {
    const ctx = this.canvasCtx;
    const w = this.canvasEl.width;
    const h = this.canvasEl.height;
    ctx.clearRect(0, 0, w, h);

    const time = now * 0.002;
    const energy = this.speechEnergy;

    // Organic Breathing & Micro-Motions
    let breath = Math.sin(time * 1.6) * 2.8;
    let swayX = Math.cos(time * 0.8) * 1.5;
    let tilt = Math.sin(time * 0.5) * 0.012; // rad

    // State-specific posture shifts
    if (this.currentStatus === 'thinking') {
      tilt += 0.035; // Thoughtful head tilt to the side
      swayX += Math.sin(time * 1.2) * 1.8;
      breath *= 0.6; // slower deep breath
    } else if (this.currentStatus === 'speaking') {
      // Lively rhythmic micro-nodding synced to speech cadence
      breath += Math.sin(time * 9.0) * (2.5 + energy * 5.0);
      swayX += Math.cos(time * 4.5) * 2.0;
    } else if (this.currentStatus === 'listening') {
      breath += 1.0; // slight lean forward
    }

    // Draw active pose or cross-fade between prev and active
    const activeImg = this.poseImages[this.activePose];
    const prevImg = this.poseImages[this.prevPose];

    ctx.save();
    // Center transformation pivot for natural head tilt/sway
    ctx.translate(w / 2 + swayX, h / 2 + breath);
    ctx.rotate(tilt);
    ctx.translate(-w / 2, -h / 2);

    if (this.transitionProgress < 1.0 && prevImg && prevImg.complete) {
      // Draw previous pose fading out
      ctx.globalAlpha = 1.0 - this.transitionProgress;
      this.drawSinglePoseImage(ctx, prevImg, w, h);

      // Draw incoming pose fading in
      if (activeImg && activeImg.complete) {
        ctx.globalAlpha = this.transitionProgress;
        this.drawSinglePoseImage(ctx, activeImg, w, h);
      }
    } else if (activeImg && activeImg.complete) {
      ctx.globalAlpha = 1.0;
      this.drawSinglePoseImage(ctx, activeImg, w, h);
    }
    ctx.globalAlpha = 1.0;

    // Natural Eye Micro-Blinking Overlay
    this.renderEyelids(ctx, w, h, now);

    // Dynamic Speech Viseme Mouth
    this.renderMouthViseme(ctx, w, h, time, energy);

    ctx.restore();
  }

  drawSinglePoseImage(ctx, img, w, h) {
    const cropW = img.naturalWidth;
    const cropH = img.naturalWidth; // Square crop
    const cropX = 0;
    const cropY = Math.max(0, img.naturalHeight * 0.02);
    ctx.drawImage(img, cropX, cropY, cropW, cropH, 0, 0, w, h);
  }

  renderEyelids(ctx, w, h, now) {
    if (!this.isBlinking) return;

    const elapsed = now - this.blinkStartTime;
    const progress = elapsed / this.blinkDuration;
    // Parabolic blink motion 0 -> 1 -> 0
    const blinkAmount = Math.sin(progress * Math.PI);

    // Eyelid coordinates matching Ray's sunglasses / eye area
    const eyeY = h * 0.36;
    const eyeHeight = 16 * blinkAmount;

    ctx.save();
    // Subtle eyelid shade blend
    ctx.fillStyle = 'rgba(28, 20, 24, 0.95)';
    
    // Left eye region
    ctx.beginPath();
    ctx.ellipse(w * 0.42, eyeY, 18, Math.max(2, eyeHeight), 0, 0, Math.PI * 2);
    ctx.fill();

    // Right eye region
    ctx.beginPath();
    ctx.ellipse(w * 0.58, eyeY, 18, Math.max(2, eyeHeight), 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  renderMouthViseme(ctx, w, h, time, energy) {
    const isSpeaking = this.currentStatus === 'speaking' || this.mouthOpen > 0.03 || this.visemeJaw > 0.04;
    if (!isSpeaking) return;

    const mouthX = w * 0.51;
    const mouthY = h * 0.442;

    const jaw = this.visemeJaw || (this.mouthOpen * 0.8) || 0;
    const spread = this.visemeSpread || (energy * 0.5) || 0;
    const sibilant = this.visemeSibilant || 0;

    // Organic vertical aperture and horizontal width
    const openH = Math.min(16, Math.max(1.8, (jaw * 13.0) + (Math.sin(time * 12.0) * 1.5) + (energy * 4.0)));
    const openW = Math.min(26, Math.max(10, 14 + (spread * 9.0) - (jaw * 2.0)));

    ctx.save();

    // 1. Subtle Chin / Jaw Micro-Drop Shadow
    if (openH > 4) {
      ctx.beginPath();
      ctx.ellipse(mouthX, mouthY + openH + 2, openW * 0.75, 4, 0, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(10, 5, 8, 0.25)';
      ctx.fill();
    }

    // 2. Oral Cavity (Dark Depth with soft falloff)
    ctx.beginPath();
    ctx.ellipse(mouthX, mouthY, openW, openH, 0, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(20, 8, 12, 0.96)';
    ctx.shadowColor = 'rgba(0, 0, 0, 0.85)';
    ctx.shadowBlur = 6;
    ctx.fill();

    // 3. Realistic Teeth Arch (Top Enamel)
    if (openH > 3.5 || sibilant > 0.3) {
      ctx.beginPath();
      const teethW = openW * 0.72;
      const teethH = Math.min(openH * 0.45, 3.2);
      ctx.rect(mouthX - (teethW / 2), mouthY - (openH * 0.65), teethW, teethH);
      ctx.fillStyle = 'rgba(242, 240, 235, 0.90)';
      ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
      ctx.shadowBlur = 2;
      ctx.fill();
    }

    // 4. Tongue Elevation (Bottom oral floor)
    if (openH > 6.0) {
      ctx.beginPath();
      ctx.ellipse(mouthX, mouthY + (openH * 0.45), openW * 0.55, openH * 0.35, 0, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(175, 65, 75, 0.75)';
      ctx.fill();
    }

    // 5. Upper Lip Contour (Natural Cupid's Bow Arch)
    ctx.beginPath();
    ctx.moveTo(mouthX - openW - 2, mouthY);
    ctx.quadraticCurveTo(mouthX - (openW * 0.4), mouthY - (openH * 0.6) - 1.5, mouthX, mouthY - (openH * 0.35));
    ctx.quadraticCurveTo(mouthX + (openW * 0.4), mouthY - (openH * 0.6) - 1.5, mouthX + openW + 2, mouthY);
    ctx.strokeStyle = 'rgba(60, 25, 35, 0.75)';
    ctx.lineWidth = 1.6;
    ctx.stroke();

    // 6. Lower Lip Contour & Subtle Highlight
    ctx.beginPath();
    ctx.ellipse(mouthX, mouthY + (openH * 0.8) + 1.2, openW * 0.85, 2.2, 0, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(180, 110, 120, 0.35)';
    ctx.fill();

    ctx.restore();
  }
}