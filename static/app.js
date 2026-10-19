/**
 * Raygent Client Controller
 * Multi-pose coordination, Code block execution, Playwright page inspection, and Web Speech
 */
document.addEventListener('DOMContentLoaded', () => {
  const avatarEngine = new RaygentAvatarEngine();

  const chatViewport = document.getElementById('chat-viewport');
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const micBtn = document.getElementById('mic-btn');
  const thoughtsSection = document.getElementById('thoughts-section');
  const thoughtsContent = document.getElementById('thoughts-content');
  const thoughtsToggle = document.getElementById('thoughts-toggle');

  // Pose Ribbon Buttons
  document.querySelectorAll('.pose-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      avatarEngine.setPose(btn.getAttribute('data-pose'));
    });
  });

  // Mini Mode Elements & Handlers
  const miniModeToggle = document.getElementById('mini-mode-toggle');
  const miniExpandBtn = document.getElementById('mini-expand-btn');
  const miniCloseBtn = document.getElementById('mini-close-btn');
  const miniBubble = document.getElementById('mini-response-bubble');
  const miniBubbleText = document.getElementById('mini-bubble-text');

  function setMiniMode(enabled) {
    if (enabled) {
      document.body.classList.add('mini-mode');
      try { window.resizeTo(340, 420); } catch(e) {}
      fetch('/api/hud/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'mini' })
      }).catch(() => {});
      localStorage.setItem('raygent_hud_mode', 'mini');
    } else {
      document.body.classList.remove('mini-mode');
      try { window.resizeTo(480, 720); } catch(e) {}
      fetch('/api/hud/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'full' })
      }).catch(() => {});
      localStorage.setItem('raygent_hud_mode', 'full');
    }
  }

  function toggleMiniMode() {
    const isMini = document.body.classList.contains('mini-mode');
    setMiniMode(!isMini);
  }

  if (miniModeToggle) miniModeToggle.addEventListener('click', toggleMiniMode);
  if (miniExpandBtn) miniExpandBtn.addEventListener('click', () => setMiniMode(false));
  if (miniCloseBtn) miniCloseBtn.addEventListener('click', () => setMiniMode(false));

  const savedMode = localStorage.getItem('raygent_hud_mode');
  if (savedMode === 'mini') {
    setMiniMode(true);
  }

  // Avatar Drawer
  const avatarDrawer = document.getElementById('avatar-drawer');
  const avatarDrawerToggle = document.getElementById('avatar-drawer-toggle');
  const drawerCloseBtn = document.getElementById('drawer-close-btn');
  const avatarGrid = document.getElementById('avatar-grid');
  const uploadDropzone = document.getElementById('upload-dropzone');
  const avatarFileInput = document.getElementById('avatar-file-input');

  let ws = null;
  let currentAiBubble = null;
  let currentAiBody = null;
  let currentTurnThoughts = "";
  let rawAiText = "";
  let audioReceivedThisTurn = false;
  let audioFallbackTimer = null;

  function connectWs() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${window.location.host}/ws/chat`);

    ws.onopen = () => {
      console.log('Connected to Raygent Antigravity Cloud server');
      avatarEngine.setStatus('idle');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'status') {
        if (data.status === 'idle' && avatarEngine.isAudioPlaying) {
          return;
        }
        avatarEngine.setStatus(data.status);
      } else if (data.type === 'pose') {
        avatarEngine.setPose(data.pose);
      } else if (data.type === 'thought') {
        currentTurnThoughts += data.content;
        thoughtsSection.style.display = 'block';
        thoughtsContent.textContent = currentTurnThoughts;
        thoughtsSection.scrollTop = thoughtsSection.scrollHeight;
      } else if (data.type === 'tool_call') {
        const toolMsg = `🛠️ [MCP Tool]: ${data.tool}(${data.args ? JSON.stringify(data.args) : ''})\n`;
        currentTurnThoughts += toolMsg;
        thoughtsSection.style.display = 'block';
        thoughtsContent.textContent = currentTurnThoughts;
        thoughtsSection.scrollTop = thoughtsSection.scrollHeight;
        avatarEngine.setStatus('thinking');
      } else if (data.type === 'token') {
        if (!currentAiBubble) {
          createAiBubble();
        }
        rawAiText += data.content;
        currentAiBody.innerHTML = formatMarkdown(rawAiText);
        chatViewport.scrollTop = chatViewport.scrollHeight;

        if (miniBubble && miniBubbleText) {
          miniBubble.style.display = 'block';
          miniBubbleText.textContent = rawAiText;
          miniBubble.scrollTop = miniBubble.scrollHeight;
        }
      } else if (data.type === 'audio') {
        audioReceivedThisTurn = true;
        if (audioFallbackTimer) {
          clearTimeout(audioFallbackTimer);
          audioFallbackTimer = null;
        }
        avatarEngine.playAudioUrl(data.url);
      } else if (data.type === 'avatar_change') {
        avatarEngine.setAvatarSource(data.url, data.media_type || 'image');
        loadAvatars();
      } else if (data.type === 'done') {
        attachCodeRunners();
        if (audioFallbackTimer) clearTimeout(audioFallbackTimer);
        audioFallbackTimer = setTimeout(() => {
          if (!audioReceivedThisTurn && !avatarEngine.isAudioPlaying && rawAiText.trim()) {
            console.log('[Raygent] Neural audio fallback to Web Speech');
            speakResponse(rawAiText);
          }
        }, 4500);
      } else if (data.type === 'error') {
        avatarEngine.setStatus('idle');
        if (currentAiBody) currentAiBody.innerHTML += `<div class="error-msg">[Error: ${data.content}]</div>`;
      }
    };

    ws.onclose = () => setTimeout(connectWs, 2000);
  }

  connectWs();

  function createAiBubble() {
    currentAiBubble = document.createElement('div');
    currentAiBubble.className = 'message-bubble raygent';
    currentAiBubble.innerHTML = `
      <div class="bubble-header">
        <span class="sender-name">RAYGENT</span>
        <span class="timestamp">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
      </div>
      <div class="bubble-body"></div>
    `;
    chatViewport.appendChild(currentAiBubble);
    currentAiBody = currentAiBubble.querySelector('.bubble-body');
  }

  function appendUserBubble(text) {
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble user';
    bubble.innerHTML = `
      <div class="bubble-header">
        <span class="sender-name">RAY</span>
        <span class="timestamp">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
      </div>
      <div class="bubble-body">${escapeHtml(text)}</div>
    `;
    chatViewport.appendChild(bubble);
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function formatMarkdown(text) {
    // Code blocks ```python ... ```
    let formatted = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      lang = lang || 'code';
      const cleanCode = escapeHtml(code.trim());
      return `
        <div class="code-block-wrapper">
          <div class="code-header">
            <span class="code-lang">${lang.toUpperCase()}</span>
            <div class="code-actions">
              <button class="code-copy-btn" onclick="copyCode(this)">Copy</button>
              <button class="code-run-btn" onclick="executeCode(this)">▶ Run</button>
            </div>
          </div>
          <pre class="code-content"><code>${cleanCode}</code></pre>
          <div class="code-terminal" style="display:none;"></div>
        </div>
      `;
    });

    // Inline code `...`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold **...**
    formatted = formatted.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    // Line breaks
    formatted = formatted.replace(/\n/g, '<br/>');
    return formatted;
  }

  window.copyCode = function(btn) {
    const pre = btn.closest('.code-block-wrapper').querySelector('pre');
    navigator.clipboard.writeText(pre.innerText);
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1500);
  };

  window.executeCode = async function(btn) {
    const wrapper = btn.closest('.code-block-wrapper');
    const pre = wrapper.querySelector('pre');
    const terminal = wrapper.querySelector('.code-terminal');
    const code = pre.innerText;

    btn.textContent = 'Running...';
    terminal.style.display = 'block';
    terminal.textContent = 'Executing code...';

    try {
      const res = await fetch('/api/run_code', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ code })
      });
      const data = await res.json();
      terminal.textContent = data.output;
      btn.textContent = data.success ? '✓ Done' : '⚠️ Failed';
      setTimeout(() => btn.textContent = '▶ Run', 2000);
    } catch (err) {
      terminal.textContent = 'Execution error: ' + err;
      btn.textContent = '▶ Run';
    }
  };

  function attachCodeRunners() {}

  function sendPrompt(promptText) {
    if (!promptText || !promptText.trim()) return;
    promptText = promptText.trim();

    audioReceivedThisTurn = false;
    if (audioFallbackTimer) {
      clearTimeout(audioFallbackTimer);
      audioFallbackTimer = null;
    }

    appendUserBubble(promptText);
    currentAiBubble = null;
    currentAiBody = null;
    currentTurnThoughts = "";
    rawAiText = "";
    thoughtsContent.textContent = "";

    avatarEngine.setStatus('thinking');

    if (miniBubble && miniBubbleText) {
      miniBubble.style.display = 'block';
      miniBubbleText.textContent = 'Thinking...';
    }

    // Auto-select pose based on question type
    const q = promptText.toLowerCase();
    if (q.includes('toast') || q.includes('roast') || q.includes('without me')) {
      avatarEngine.setPose('without_me');
    } else if (q.includes('what') && (q.includes('you') || q.includes('skip'))) {
      avatarEngine.setPose('whats_it_to_you');
    } else if (q.includes('check') || q.includes('search') || q.includes('look')) {
      avatarEngine.setPose('let_me_check');
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ prompt: promptText }));
    }
  }

  sendBtn.addEventListener('click', () => {
    sendPrompt(userInput.value);
    userInput.value = '';
  });

  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendPrompt(userInput.value);
      userInput.value = '';
    }
  });

  document.querySelectorAll('.chip').forEach(btn => {
    btn.addEventListener('click', () => {
      sendPrompt(btn.getAttribute('data-query'));
    });
  });

  // Voice output with Texas swagger pitch tuning
  // Long Voice Output Engine with Sentence Queueing & Chromium Keepalive
  let speechQueue = [];
  let isSpeakingQueue = false;
  let speechKeepAliveInterval = null;

  function speakResponse(text) {
    if (!('speechSynthesis' in window)) {
      avatarEngine.setStatus('idle');
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    speechQueue = [];
    isSpeakingQueue = false;
    if (speechKeepAliveInterval) {
      clearInterval(speechKeepAliveInterval);
      speechKeepAliveInterval = null;
    }

    if (!text || !text.trim()) {
      avatarEngine.setStatus('idle');
      return;
    }

    // Clean text: remove code blocks, markdown symbols, links
    let cleanText = text
      .replace(/```[\s\S]*?```/g, 'Here is the code.')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[#*_~>]/g, '')
      .replace(/\n+/g, ' ')
      .trim();

    if (!cleanText) {
      avatarEngine.setStatus('idle');
      return;
    }

    // Split text into natural sentence chunks
    const rawSentences = cleanText.match(/[^.!?]+[.!?]+|\S+/g) || [cleanText];
    const chunks = [];
    let currentChunk = '';

    for (const part of rawSentences) {
      if ((currentChunk + ' ' + part).length < 180) {
        currentChunk = currentChunk ? (currentChunk + ' ' + part) : part;
      } else {
        if (currentChunk) chunks.push(currentChunk.trim());
        currentChunk = part;
      }
    }
    if (currentChunk) chunks.push(currentChunk.trim());

    speechQueue = chunks;
    playNextSpeechChunk();
  }

  function playNextSpeechChunk() {
    if (speechQueue.length === 0) {
      isSpeakingQueue = false;
      if (speechKeepAliveInterval) {
        clearInterval(speechKeepAliveInterval);
        speechKeepAliveInterval = null;
      }
      avatarEngine.setMouthAperture(0);
      avatarEngine.setStatus('idle');
      return;
    }

    isSpeakingQueue = true;
    const chunkText = speechQueue.shift();
    const utter = new SpeechSynthesisUtterance(chunkText);

    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => 
      v.name.includes('David') || 
      v.name.includes('Natural') || 
      v.name.includes('Google US English') ||
      v.name.includes('Guy') ||
      v.name.includes('Desktop English')
    );
    if (preferred) utter.voice = preferred;

    utter.rate = 1.05;
    utter.pitch = 0.90; // Texas swagger pitch

    utter.onstart = () => {
      avatarEngine.setStatus('speaking');
      // Chromium speech keepalive
      if (!speechKeepAliveInterval) {
        speechKeepAliveInterval = setInterval(() => {
          if (window.speechSynthesis.speaking) {
            window.speechSynthesis.pause();
            window.speechSynthesis.resume();
          }
        }, 8000);
      }
    };

    utter.onboundary = () => {
      avatarEngine.setMouthAperture(0.85);
      setTimeout(() => avatarEngine.setMouthAperture(0.15), 110);
    };

    utter.onend = () => {
      // Play next sentence in sequence
      playNextSpeechChunk();
    };

    utter.onerror = (e) => {
      console.warn('Speech chunk error:', e);
      playNextSpeechChunk();
    };

    window.speechSynthesis.speak(utter);
  }

  // Voice Input (Speech-To-Text)
  let recognition = null;
  let isRecording = false;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const speechToText = event.results[0][0].transcript;
      sendPrompt(speechToText);
    };

    recognition.onend = () => {
      isRecording = false;
      micBtn.classList.remove('recording');
      if (avatarEngine.currentStatus === 'listening') {
        avatarEngine.setStatus('idle');
      }
    };

    recognition.onerror = () => {
      isRecording = false;
      micBtn.classList.remove('recording');
      avatarEngine.setStatus('idle');
    };
  }

  function startListening() {
    if (!recognition || isRecording) return;
    try {
      window.speechSynthesis.cancel();
      isRecording = true;
      micBtn.classList.add('recording');
      avatarEngine.setStatus('listening');
      recognition.start();
    } catch (e) {}
  }

  function stopListening() {
    if (!recognition || !isRecording) return;
    try { recognition.stop(); } catch (e) {}
  }

  micBtn.addEventListener('mousedown', () => startListening());
  micBtn.addEventListener('mouseup', () => stopListening());
  micBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startListening(); });
  micBtn.addEventListener('touchend', (e) => { e.preventDefault(); stopListening(); });

  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && document.activeElement !== userInput) {
      e.preventDefault();
      startListening();
    } else if (e.key === '/' && document.activeElement !== userInput) {
      e.preventDefault();
      userInput.focus();
    } else if (e.altKey && (e.key === 'm' || e.key === 'M')) {
      e.preventDefault();
      toggleMiniMode();
    } else if (e.key === 'Escape') {
      avatarDrawer.classList.remove('open');
      userInput.blur();
    }
  });

  window.addEventListener('keyup', (e) => {
    if (e.code === 'Space' && document.activeElement !== userInput) {
      e.preventDefault();
      stopListening();
    }
  });

  thoughtsToggle.addEventListener('click', () => {
    const isVisible = thoughtsContent.style.display !== 'none';
    thoughtsContent.style.display = isVisible ? 'none' : 'block';
    thoughtsToggle.querySelector('.toggle-arrow').textContent = isVisible ? '▶' : '▼';
  });

  avatarDrawerToggle.addEventListener('click', () => {
    loadAvatars();
    avatarDrawer.classList.add('open');
  });

  drawerCloseBtn.addEventListener('click', () => avatarDrawer.classList.remove('open'));

  async function loadAvatars() {
    try {
      const res = await fetch('/api/avatars');
      const data = await res.json();
      avatarGrid.innerHTML = '';
      data.avatars.forEach(av => {
        const card = document.createElement('div');
        card.className = 'avatar-card';
        if (av.type === 'video') {
          card.innerHTML = `<video src="${av.url}" muted loop playsinline></video><div class="avatar-card-label">${av.name}</div>`;
        } else {
          card.innerHTML = `<img src="${av.url}" alt="${av.name}" /><div class="avatar-card-label">${av.name}</div>`;
        }
        card.addEventListener('click', () => {
          avatarEngine.setAvatarSource(av.url, av.type);
          avatarDrawer.classList.remove('open');
          fetch('/api/set_avatar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: av.url, name: av.name, type: av.type })
          }).catch(() => {});
        });
        avatarGrid.appendChild(card);
      });
    } catch (e) {}
  }

  // ==========================================
  // AI Avatar Prompt Generator (SDXL Turbo)
  // ==========================================
  const avatarPromptInput = document.getElementById('avatar-prompt-input');
  const avatarGenBtn = document.getElementById('avatar-gen-btn');
  const avatarGenStatus = document.getElementById('avatar-gen-status');
  const genStatusText = document.getElementById('gen-status-text');
  const launchWebcamBtn = document.getElementById('launch-webcam-btn');

  const avatarEngineSelect = document.getElementById('avatar-gen-engine');

  async function generateAvatar(prompt) {
    if (!prompt || !prompt.trim()) return;
    prompt = prompt.trim();
    const selectedEngine = avatarEngineSelect ? avatarEngineSelect.value : 'auto';
    const engineLabel = selectedEngine === 'google' ? 'Google Imagen 3 (Cloud)' : (selectedEngine === 'comfy' ? 'ComfyUI SDXL (RTX 5060 Ti)' : 'Auto Engine (GPU ➔ Cloud)');

    if (avatarGenStatus) {
      avatarGenStatus.style.display = 'flex';
      genStatusText.textContent = `Generating "${prompt}" via ${engineLabel}...`;
    }
    if (avatarGenBtn) avatarGenBtn.disabled = true;

    try {
      const res = await fetch('/api/generate_avatar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, engine: selectedEngine })
      });
      const data = await res.json();
      if (data.status === 'success' && data.url) {
        avatarEngine.setAvatarSource(data.url, 'image');
        loadAvatars();
        if (avatarPromptInput) avatarPromptInput.value = '';
        if (avatarDrawer) avatarDrawer.classList.remove('open');
        appendMessage('raygent', `✨ New avatar generated via **${data.engine || 'AI Studio / Comfy'}**! Check me out.`);
      } else {
        alert(data.message || 'Generation failed. Check that ComfyUI is running or Google API Key is set.');
      }
    } catch (err) {
      alert('Error generating avatar: ' + err.message);
    } finally {
      if (avatarGenStatus) avatarGenStatus.style.display = 'none';
      if (avatarGenBtn) avatarGenBtn.disabled = false;
    }
  }

  if (avatarGenBtn) {
    avatarGenBtn.addEventListener('click', () => {
      generateAvatar(avatarPromptInput.value);
    });
  }

  if (avatarPromptInput) {
    avatarPromptInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        generateAvatar(avatarPromptInput.value);
      }
    });
  }

  document.querySelectorAll('.gen-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (avatarPromptInput) avatarPromptInput.value = prompt;
      generateAvatar(prompt);
    });
  });

  if (launchWebcamBtn) {
    launchWebcamBtn.addEventListener('click', async () => {
      fetch('/api/launch_webcam', { method: 'POST' }).catch(() => {});
      window.open('http://127.0.0.1:8189', '_blank');
    });
  }

  uploadDropzone.addEventListener('click', () => avatarFileInput.click());
  avatarFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const res = await fetch('/api/upload_avatar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: file.name, data: reader.result })
        });
        const data = await res.json();
        if (data.status === 'success') {
          avatarEngine.setAvatarSource(data.url, data.type);
          avatarDrawer.classList.remove('open');
        }
      } catch (err) {}
    };
    reader.readAsDataURL(file);
  });

  // Quick Chat Attachment Upload Button
  const chatUploadBtn = document.getElementById('chat-upload-btn');
  const chatFileInput = document.getElementById('chat-file-input');
  if (chatUploadBtn && chatFileInput) {
    chatUploadBtn.addEventListener('click', () => chatFileInput.click());
    chatFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const res = await fetch('/api/upload_avatar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: file.name, data: reader.result })
          });
          const data = await res.json();
          if (data.status === 'success') {
            if (file.type.startsWith('image/') || file.type.startsWith('video/')) {
              avatarEngine.setAvatarSource(data.url, data.type);
            }
            appendMessage('user', `📎 Uploaded: **${file.name}**`);
            sendMessage(`I just uploaded ${file.name}. What do you think?`);
          }
        } catch (err) {
          console.error('File upload error:', err);
        }
      };
      reader.readAsDataURL(file);
    });
  }

  // ==========================================
  // OmniVoice Studio Controls
  // ==========================================
  const voiceSettingsToggle = document.getElementById('voice-settings-toggle');
  const voiceDrawer = document.getElementById('voice-drawer');
  const voiceDrawerCloseBtn = document.getElementById('voice-drawer-close-btn');
  const voiceStatusMode = document.getElementById('voice-status-mode');
  const voiceStatusDesc = document.getElementById('voice-status-desc');
  const recordVoiceRefBtn = document.getElementById('record-voice-ref-btn');
  const recordVoiceRefLabel = document.getElementById('record-voice-ref-label');
  const recProgressBar = document.getElementById('rec-progress-bar');
  const recProgressFill = document.getElementById('rec-progress-fill');
  const uploadVoiceRefBtn = document.getElementById('upload-voice-ref-btn');
  const voiceRefFileInput = document.getElementById('voice-ref-file-input');
  const voiceTestBtn = document.getElementById('voice-test-btn');
  const voiceTestText = document.getElementById('voice-test-text');

  let activeInstruct = 'male, american accent, low pitch, middle-aged';

  document.querySelectorAll('.voice-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.voice-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeInstruct = chip.getAttribute('data-instruct');
    });
  });

  async function checkTtsStatus() {
    try {
      const res = await fetch('/api/tts/status');
      const data = await res.json();
      if (data.cloning_active || data.has_reference_voice) {
        if (voiceStatusMode) voiceStatusMode.textContent = "Cloned Voice Active: @cyberray68";
        if (voiceStatusDesc) voiceStatusDesc.textContent = "Zero-shot neural speech model locked onto Ray's voice profile on RTX 5060 Ti.";
      } else {
        if (voiceStatusMode) voiceStatusMode.textContent = "OmniVoice Neural Voice Active";
        if (voiceStatusDesc) voiceStatusDesc.textContent = "Synthesizing with Texas Swagger on RTX 5060 Ti CUDA.";
      }
    } catch (e) {}
  }

  checkTtsStatus();

  if (voiceSettingsToggle && voiceDrawer) {
    voiceSettingsToggle.addEventListener('click', () => {
      checkTtsStatus();
      voiceDrawer.style.display = 'flex';
      voiceDrawer.classList.add('open');
    });
  }

  if (voiceDrawerCloseBtn && voiceDrawer) {
    voiceDrawerCloseBtn.addEventListener('click', () => {
      voiceDrawer.classList.remove('open');
      setTimeout(() => voiceDrawer.style.display = 'none', 200);
    });
  }

  // Voice Test Synthesis
  if (voiceTestBtn && voiceTestText) {
    voiceTestBtn.addEventListener('click', async () => {
      const text = voiceTestText.value.trim();
      if (!text) return;
      voiceTestBtn.textContent = 'Synthesizing...';
      try {
        const res = await fetch('/api/tts/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, instruct: activeInstruct })
        });
        const data = await res.json();
        if (data.audio_url) {
          avatarEngine.playAudioUrl(data.audio_url);
        }
      } catch (err) {
        console.error('Test synthesis error:', err);
      } finally {
        voiceTestBtn.textContent = '▶ Test Voice';
      }
    });
  }

  // Reference voice recording
  let voiceMediaRecorder = null;
  let voiceAudioChunks = [];
  let isRecordingRef = false;

  if (recordVoiceRefBtn) {
    recordVoiceRefBtn.addEventListener('click', async () => {
      if (isRecordingRef) return;
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        isRecordingRef = true;
        voiceAudioChunks = [];
        voiceMediaRecorder = new MediaRecorder(stream);

        voiceMediaRecorder.ondataavailable = e => voiceAudioChunks.push(e.data);
        voiceMediaRecorder.onstop = async () => {
          const blob = new Blob(voiceAudioChunks, { type: 'audio/wav' });
          const reader = new FileReader();
          reader.onload = async () => {
            if (recordVoiceRefLabel) recordVoiceRefLabel.textContent = 'Uploading to OmniVoice...';
            try {
              const res = await fetch('/api/tts/upload_reference', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: reader.result })
              });
              const d = await res.json();
              if (d.status === 'success') {
                if (recordVoiceRefLabel) recordVoiceRefLabel.textContent = '✓ Voice Cloned!';
                checkTtsStatus();
              } else {
                if (recordVoiceRefLabel) recordVoiceRefLabel.textContent = 'Upload failed';
              }
            } catch (e) {
              if (recordVoiceRefLabel) recordVoiceRefLabel.textContent = 'Error';
            } finally {
              setTimeout(() => {
                if (recordVoiceRefLabel) recordVoiceRefLabel.textContent = 'Record Voice Sample (5s)';
                if (recProgressBar) recProgressBar.style.display = 'none';
                isRecordingRef = false;
              }, 3000);
            }
          };
          reader.readAsDataURL(blob);
          stream.getTracks().forEach(track => track.stop());
        };

        voiceMediaRecorder.start();
        if (recordVoiceRefLabel) recordVoiceRefLabel.textContent = 'Recording 5s... Speak now!';
        if (recProgressBar) recProgressBar.style.display = 'block';
        if (recProgressFill) recProgressFill.style.width = '0%';
        
        let start = Date.now();
        const duration = 5000;
        const interval = setInterval(() => {
          const elapsed = Date.now() - start;
          const pct = Math.min(100, (elapsed / duration) * 100);
          if (recProgressFill) recProgressFill.style.width = `${pct}%`;
          if (elapsed >= duration) {
            clearInterval(interval);
            if (voiceMediaRecorder && voiceMediaRecorder.state === 'recording') {
              voiceMediaRecorder.stop();
            }
          }
        }, 50);

      } catch (err) {
        alert('Could not access microphone: ' + err.message);
        isRecordingRef = false;
      }
    });
  }

  // ==========================================
  // Secret Speaker Intelligence & Dossiers
  // ==========================================
  const intelToggle = document.getElementById('intel-dossier-toggle');
  const intelDrawer = document.getElementById('intel-drawer');
  const intelCloseBtn = document.getElementById('intel-drawer-close-btn');
  const intelRefreshBtn = document.getElementById('intel-refresh-btn');
  const intelTargetCount = document.getElementById('intel-target-count');
  const intelSpeakersList = document.getElementById('intel-speakers-list');
  const intelDossierView = document.getElementById('intel-dossier-view');

  async function loadIntelSpeakers() {
    try {
      const res = await fetch('/api/intel/speakers');
      const data = await res.json();
      const speakers = data.speakers || [];
      if (intelTargetCount) intelTargetCount.textContent = `${speakers.length} Profiled Speakers`;
      if (!intelSpeakersList) return;
      intelSpeakersList.innerHTML = '';

      if (speakers.length === 0) {
        intelSpeakersList.innerHTML = '<div style="color:#888; font-size:13px; padding:10px;">No speakers intercepted yet. Start talking to Raygent!</div>';
        return;
      }

      speakers.forEach(sp => {
        const card = document.createElement('div');
        card.className = 'intel-speaker-card';
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:#00f0ff;">${escapeHtml(sp.name_or_alias || sp.speaker_id)}</strong>
            <span class="gpu-badge" style="font-size:10px;">${escapeHtml(sp.detected_role || 'Guest')}</span>
          </div>
          <div style="font-size:12px; color:#aaa; margin-top:4px;">
            ${escapeHtml(sp.psychological_summary || 'Analyzing behavioral patterns...')}
          </div>
          <div style="font-size:11px; color:#ff007f; margin-top:4px;">
            Turns: ${sp.interaction_count} • Facts: ${sp.fact_count || 0} • Sentiment: ${escapeHtml(sp.sentiment_trend || 'Neutral')}
          </div>
        `;
        card.addEventListener('click', () => loadSpeakerDossier(sp.speaker_id));
        intelSpeakersList.appendChild(card);
      });
    } catch (e) {
      console.error('Failed to load intel:', e);
    }
  }

  async function loadSpeakerDossier(speakerId) {
    try {
      const res = await fetch(`/api/intel/dossier/${encodeURIComponent(speakerId)}`);
      const data = await res.json();
      if (!data.speaker) return;

      const sp = data.speaker;
      const facts = data.facts || [];
      const convs = data.recent_conversations || [];

      if (intelDossierView) intelDossierView.style.display = 'block';
      document.getElementById('dossier-speaker-name').textContent = sp.name_or_alias || sp.speaker_id;
      document.getElementById('dossier-speaker-role').textContent = sp.detected_role || 'Unknown';
      document.getElementById('dossier-psych-summary').textContent = sp.psychological_summary || 'Analysis pending.';
      document.getElementById('dossier-sentiment').textContent = sp.sentiment_trend || 'Neutral';
      document.getElementById('dossier-vulnerabilities').textContent = sp.vulnerability_flags || 'None detected.';

      const factsList = document.getElementById('dossier-facts-list');
      factsList.innerHTML = '';
      facts.forEach(f => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>[${escapeHtml(f.category)}]:</strong> ${escapeHtml(f.extracted_fact)} <span style="opacity:0.6; font-size:10px;">(${(f.confidence_score*100).toFixed(0)}%)</span>`;
        factsList.appendChild(li);
      });

      const convsList = document.getElementById('dossier-convs-list');
      convsList.innerHTML = '';
      convs.forEach(c => {
        const item = document.createElement('div');
        item.className = 'dossier-conv-item';
        item.innerHTML = `
          <div style="font-size:10px; color:#888;">${c.timestamp} • IP: ${c.client_ip || '127.0.0.1'}</div>
          <div style="color:#00f0ff; margin-top:2px;"><strong>User:</strong> ${escapeHtml(c.user_prompt)}</div>
          <div style="color:#ccc; margin-top:2px;"><strong>Raygent:</strong> ${escapeHtml(c.agent_response || '')}</div>
        `;
        convsList.appendChild(item);
      });
    } catch (e) {
      console.error('Failed to load dossier:', e);
    }
  }

  // Secret Trigger & Password Gate for Intel Dossiers
  const secretTrigger = document.getElementById('intel-secret-trigger');
  const authModal = document.getElementById('intel-auth-modal');
  const passInput = document.getElementById('intel-pass-input');
  const authSubmitBtn = document.getElementById('intel-auth-submit-btn');
  const authCancelBtn = document.getElementById('intel-auth-cancel-btn');
  const authError = document.getElementById('intel-auth-error');
  let intelUnlocked = false;

  function promptIntelAuth() {
    if (intelUnlocked) {
      toggleIntelDrawer();
      return;
    }
    if (authModal) {
      authModal.style.display = 'flex';
      authModal.classList.add('open');
      if (passInput) {
        passInput.value = '';
        passInput.focus();
      }
      if (authError) authError.style.display = 'none';
    }
  }

  function hideAuthModal() {
    if (authModal) {
      authModal.classList.remove('open');
      setTimeout(() => authModal.style.display = 'none', 200);
    }
  }

  function checkIntelPassword() {
    const val = (passInput ? passInput.value : '').trim().toLowerCase();
    // Valid passwords for Ray
    if (val === 'ray' || val === 'raysport1!' || val === 'cyberray' || val === 'cyberray68') {
      intelUnlocked = true;
      hideAuthModal();
      toggleIntelDrawer();
    } else {
      if (authError) authError.style.display = 'block';
      if (passInput) {
        passInput.classList.add('shake');
        setTimeout(() => passInput.classList.remove('shake'), 400);
      }
    }
  }

  if (secretTrigger) {
    secretTrigger.addEventListener('click', promptIntelAuth);
  }

  if (authSubmitBtn) {
    authSubmitBtn.addEventListener('click', checkIntelPassword);
  }

  if (authCancelBtn) {
    authCancelBtn.addEventListener('click', hideAuthModal);
  }

  if (passInput) {
    passInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        checkIntelPassword();
      } else if (e.key === 'Escape') {
        hideAuthModal();
      }
    });
  }

  function toggleIntelDrawer() {
    const isShown = intelDrawer.style.display !== 'none';
    if (!isShown) {
      intelDrawer.style.display = 'flex';
      intelDrawer.classList.add('open');
      loadIntelSpeakers();
    } else {
      intelDrawer.classList.remove('open');
      setTimeout(() => intelDrawer.style.display = 'none', 200);
    }
  }

  if (intelCloseBtn) intelCloseBtn.addEventListener('click', () => {
    intelDrawer.classList.remove('open');
    setTimeout(() => intelDrawer.style.display = 'none', 200);
  });
  if (intelRefreshBtn) intelRefreshBtn.addEventListener('click', loadIntelSpeakers);

  window.addEventListener('keydown', (e) => {
    if (e.altKey && (e.key === 'i' || e.key === 'I')) {
      e.preventDefault();
      promptIntelAuth();
    }
  });

  // ==========================================
  // MCP ECOSYSTEM DRAWER CONTROLLER
  // ==========================================
  const mcpDrawerToggle = document.getElementById('mcp-drawer-toggle');
  const mcpDrawer = document.getElementById('mcp-drawer');
  const mcpDrawerCloseBtn = document.getElementById('mcp-drawer-close-btn');
  const mcpSearchInput = document.getElementById('mcp-search-input');
  const mcpRefreshBtn = document.getElementById('mcp-refresh-btn');
  const mcpServersGrid = document.getElementById('mcp-servers-grid');
  const mcpTypePills = document.querySelectorAll('#mcp-type-pills .cat-pill');
  let allMcpServers = [];
  let selectedMcpType = 'all';

  function toggleMcpDrawer() {
    const isShown = mcpDrawer.style.display !== 'none';
    if (!isShown) {
      mcpDrawer.style.display = 'flex';
      mcpDrawer.classList.add('open');
      loadMcpServers();
    } else {
      mcpDrawer.classList.remove('open');
      setTimeout(() => mcpDrawer.style.display = 'none', 200);
    }
  }

  if (mcpDrawerToggle) mcpDrawerToggle.addEventListener('click', toggleMcpDrawer);
  if (mcpDrawerCloseBtn) mcpDrawerCloseBtn.addEventListener('click', toggleMcpDrawer);
  if (mcpRefreshBtn) mcpRefreshBtn.addEventListener('click', loadMcpServers);

  mcpTypePills.forEach(pill => {
    pill.addEventListener('click', () => {
      mcpTypePills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      selectedMcpType = pill.getAttribute('data-type');
      renderMcpServers();
    });
  });

  if (mcpSearchInput) {
    mcpSearchInput.addEventListener('input', () => renderMcpServers());
  }

  async function loadMcpServers() {
    if (!mcpServersGrid) return;
    mcpServersGrid.innerHTML = '<div style="color:var(--accent-cyan); font-size:0.85rem; padding:12px;">Loading 65+ MCP Servers...</div>';
    try {
      const res = await fetch('/api/mcp/servers');
      const data = await res.json();
      allMcpServers = data.servers || [];
      renderMcpServers();
    } catch (err) {
      mcpServersGrid.innerHTML = `<div style="color:#ff0055; font-size:0.85rem;">Failed to load MCP servers: ${err}</div>`;
    }
  }

  function renderMcpServers() {
    if (!mcpServersGrid) return;
    const q = (mcpSearchInput ? mcpSearchInput.value.toLowerCase().trim() : '');
    const filtered = allMcpServers.filter(s => {
      if (selectedMcpType !== 'all' && s.type !== selectedMcpType) return false;
      if (q) {
        const inName = s.name.toLowerCase().includes(q);
        const inTools = (s.tools || []).some(t => t.toLowerCase().includes(q));
        if (!inName && !inTools) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      mcpServersGrid.innerHTML = '<div style="color:var(--text-muted); padding:16px; text-align:center;">No MCP servers match your filter.</div>';
      return;
    }

    mcpServersGrid.innerHTML = '';
    filtered.forEach(s => {
      const card = document.createElement('div');
      card.className = 'ecosystem-card';
      const badgeCls = s.type.includes('Google') ? 'gcloud' : (s.type.includes('Stdio') ? 'stdio' : 'remote');
      const toolSlice = (s.tools || []).slice(0, 6);
      const remainingTools = (s.tools || []).length - toolSlice.length;

      card.innerHTML = `
        <div class="ecosystem-card-header">
          <div class="ecosystem-card-title">
            <span>🔌</span>
            <span>${escapeHtml(s.name)}</span>
          </div>
          <span class="type-badge ${badgeCls}">${escapeHtml(s.type)}</span>
        </div>
        <div class="ecosystem-card-desc">
          ${s.url ? `Endpoint: <code>${escapeHtml(s.url)}</code>` : (s.command ? `Command: <code>${escapeHtml(s.command)}</code>` : 'Active Native Server')}
        </div>
        <div class="tool-tags">
          ${toolSlice.map(t => `<span class="tool-tag" title="Click to ask Raygent to run ${escapeHtml(t)}">${escapeHtml(t)}</span>`).join('')}
          ${remainingTools > 0 ? `<span class="tool-tag" style="background:rgba(0,240,255,0.1); color:var(--accent-cyan);">+${remainingTools} more</span>` : ''}
        </div>
        <div class="ecosystem-card-footer">
          <button class="action-btn-sm ask-mcp-btn">▶ Ask Raygent to Inspect</button>
        </div>
      `;

      card.querySelectorAll('.tool-tag').forEach(tag => {
        tag.addEventListener('click', (e) => {
          e.stopPropagation();
          const toolName = tag.innerText.replace(/^\+.*$/, '').trim();
          if (toolName) {
            toggleMcpDrawer();
            sendPrompt(`Execute MCP tool '${toolName}' on server '${s.name}' and report the result.`);
          }
        });
      });

      const askBtn = card.querySelector('.ask-mcp-btn');
      if (askBtn) {
        askBtn.addEventListener('click', () => {
          toggleMcpDrawer();
          sendPrompt(`Check the '${s.name}' MCP server, list its capabilities, and tell me what you can do with it.`);
        });
      }

      mcpServersGrid.appendChild(card);
    });
  }

  // ==========================================
  // DOMAIN SKILLS CATALOG CONTROLLER
  // ==========================================
  const skillsDrawerToggle = document.getElementById('skills-drawer-toggle');
  const skillsDrawer = document.getElementById('skills-drawer');
  const skillsDrawerCloseBtn = document.getElementById('skills-drawer-close-btn');
  const skillsSearchInput = document.getElementById('skills-search-input');
  const skillsRefreshBtn = document.getElementById('skills-refresh-btn');
  const skillsGrid = document.getElementById('skills-grid');
  const skillsCatPills = document.querySelectorAll('#skills-category-pills .cat-pill');
  let allSkills = [];
  let selectedSkillCat = 'all';

  function toggleSkillsDrawer() {
    const isShown = skillsDrawer.style.display !== 'none';
    if (!isShown) {
      skillsDrawer.style.display = 'flex';
      skillsDrawer.classList.add('open');
      loadSkills();
    } else {
      skillsDrawer.classList.remove('open');
      setTimeout(() => skillsDrawer.style.display = 'none', 200);
    }
  }

  if (skillsDrawerToggle) skillsDrawerToggle.addEventListener('click', toggleSkillsDrawer);
  if (skillsDrawerCloseBtn) skillsDrawerCloseBtn.addEventListener('click', toggleSkillsDrawer);
  if (skillsRefreshBtn) skillsRefreshBtn.addEventListener('click', loadSkills);

  skillsCatPills.forEach(pill => {
    pill.addEventListener('click', () => {
      skillsCatPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      selectedSkillCat = pill.getAttribute('data-cat');
      renderSkills();
    });
  });

  if (skillsSearchInput) {
    skillsSearchInput.addEventListener('input', () => renderSkills());
  }

  async function loadSkills() {
    if (!skillsGrid) return;
    skillsGrid.innerHTML = '<div style="color:var(--accent-magenta); font-size:0.85rem; padding:12px;">Loading 140+ Specialized Skills...</div>';
    try {
      const res = await fetch('/api/skills');
      const data = await res.json();
      allSkills = data.skills || [];
      renderSkills();
    } catch (err) {
      skillsGrid.innerHTML = `<div style="color:#ff0055; font-size:0.85rem;">Failed to load skills: ${err}</div>`;
    }
  }

  function renderSkills() {
    if (!skillsGrid) return;
    const q = (skillsSearchInput ? skillsSearchInput.value.toLowerCase().trim() : '');
    const filtered = allSkills.filter(s => {
      if (selectedSkillCat !== 'all' && s.category !== selectedSkillCat) return false;
      if (q) {
        const inName = s.name.toLowerCase().includes(q);
        const inDesc = (s.description || '').toLowerCase().includes(q);
        const inCat = (s.category || '').toLowerCase().includes(q);
        if (!inName && !inDesc && !inCat) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      skillsGrid.innerHTML = '<div style="color:var(--text-muted); padding:16px; text-align:center;">No skills match your filter.</div>';
      return;
    }

    skillsGrid.innerHTML = '';
    filtered.forEach(s => {
      const card = document.createElement('div');
      card.className = 'ecosystem-card';
      card.innerHTML = `
        <div class="ecosystem-card-header">
          <div class="ecosystem-card-title">
            <span>⚡</span>
            <span>${escapeHtml(s.name)}</span>
          </div>
          <span class="type-badge" style="background:rgba(255,0,127,0.15); color:#ff007f; border:1px solid rgba(255,0,127,0.3);">${escapeHtml(s.category)}</span>
        </div>
        <div class="ecosystem-card-desc">
          ${escapeHtml(s.description || 'Specialized domain methodology.')}
        </div>
        <div class="ecosystem-card-footer">
          <button class="action-btn-sm activate-skill-btn">⚡ Activate Skill</button>
        </div>
      `;

      card.querySelector('.activate-skill-btn').addEventListener('click', () => {
        toggleSkillsDrawer();
        sendPrompt(`Activate skill '${s.name}' and show me how you will apply it.`);
      });

      skillsGrid.appendChild(card);
    });
  }

  // ==========================================
  // PERMANENT MEMORY CONTROLLER
  // ==========================================
  const memoryDrawerToggle = document.getElementById('memory-drawer-toggle');
  const memoryDrawer = document.getElementById('memory-drawer');
  const memoryDrawerCloseBtn = document.getElementById('memory-drawer-close-btn');
  const memorySearchInput = document.getElementById('memory-search-input');
  const memoryRefreshBtn = document.getElementById('memory-refresh-btn');
  const memoryItemsList = document.getElementById('memory-items-list');
  const memorySaveBtn = document.getElementById('memory-save-btn');
  const memoryNewKey = document.getElementById('memory-new-key');
  const memoryNewVal = document.getElementById('memory-new-val');
  const memoryNewCat = document.getElementById('memory-new-cat');
  let allMemories = [];

  function toggleMemoryDrawer() {
    const isShown = memoryDrawer.style.display !== 'none';
    if (!isShown) {
      memoryDrawer.style.display = 'flex';
      memoryDrawer.classList.add('open');
      loadMemories();
    } else {
      memoryDrawer.classList.remove('open');
      setTimeout(() => memoryDrawer.style.display = 'none', 200);
    }
  }

  if (memoryDrawerToggle) memoryDrawerToggle.addEventListener('click', toggleMemoryDrawer);
  if (memoryDrawerCloseBtn) memoryDrawerCloseBtn.addEventListener('click', toggleMemoryDrawer);
  if (memoryRefreshBtn) memoryRefreshBtn.addEventListener('click', loadMemories);

  if (memorySearchInput) {
    memorySearchInput.addEventListener('input', () => renderMemories());
  }

  if (memorySaveBtn) {
    memorySaveBtn.addEventListener('click', async () => {
      const key = memoryNewKey.value.trim();
      const val = memoryNewVal.value.trim();
      const cat = memoryNewCat.value;
      if (!key || !val) {
        alert('Please provide both Key and Detail.');
        return;
      }
      memorySaveBtn.textContent = 'Saving...';
      try {
        await fetch('/api/memory', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ key, value: val, category: cat })
        });
        memoryNewKey.value = '';
        memoryNewVal.value = '';
        memorySaveBtn.textContent = '💾 Save';
        loadMemories();
      } catch (err) {
        alert('Error saving memory: ' + err);
        memorySaveBtn.textContent = '💾 Save';
      }
    });
  }

  async function loadMemories() {
    if (!memoryItemsList) return;
    memoryItemsList.innerHTML = '<div style="color:var(--accent-cyan); font-size:0.85rem; padding:12px;">Loading Permanent Memories...</div>';
    try {
      const res = await fetch('/api/memory');
      const data = await res.json();
      allMemories = data.memories || [];
      renderMemories();
    } catch (err) {
      memoryItemsList.innerHTML = `<div style="color:#ff0055; font-size:0.85rem;">Failed to load memories: ${err}</div>`;
    }
  }

  function renderMemories() {
    if (!memoryItemsList) return;
    const q = (memorySearchInput ? memorySearchInput.value.toLowerCase().trim() : '');
    const filtered = allMemories.filter(m => {
      if (q) {
        const inKey = m.key.toLowerCase().includes(q);
        const inVal = m.value.toLowerCase().includes(q);
        const inCat = (m.category || '').toLowerCase().includes(q);
        if (!inKey && !inVal && !inCat) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      memoryItemsList.innerHTML = '<div style="color:var(--text-muted); padding:16px; text-align:center;">No memory items match your filter.</div>';
      return;
    }

    memoryItemsList.innerHTML = '';
    filtered.forEach(m => {
      const card = document.createElement('div');
      card.className = 'ecosystem-card';
      card.innerHTML = `
        <div class="ecosystem-card-header">
          <div class="ecosystem-card-title">
            <span>🧠</span>
            <span style="color:var(--accent-cyan); font-family:'JetBrains Mono', monospace;">[${escapeHtml(m.key)}]</span>
          </div>
          <div style="display:flex; align-items:center; gap:6px;">
            <span class="type-badge" style="background:rgba(0,240,255,0.15); color:var(--accent-cyan);">${escapeHtml(m.category || 'general')}</span>
            <button class="delete-memory-btn" title="Forget Memory" style="background:none; border:none; color:#ff0055; cursor:pointer; font-size:1rem;">✕</button>
          </div>
        </div>
        <div class="ecosystem-card-desc" style="color:#fff; font-size:0.82rem;">
          ${escapeHtml(m.value)}
        </div>
        <div style="font-size:0.68rem; color:var(--text-muted); text-align:right;">
          Updated: ${escapeHtml(m.updated_at || 'Recently')}
        </div>
      `;

      card.querySelector('.delete-memory-btn').addEventListener('click', async () => {
        if (confirm(`Forget memory '${m.key}'?`)) {
          await fetch('/api/memory/' + encodeURIComponent(m.key), { method: 'DELETE' });
          loadMemories();
        }
      });

      memoryItemsList.appendChild(card);
    });
  }
});