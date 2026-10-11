/**
 * NimbleBuddy - Frontend Application Script
 * Hackathon-ready interactive agent UI with live tool inspector
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- DOM Elements ---
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const welcomeCard = document.getElementById('welcomeCard');
  const statusBadge = document.getElementById('statusBadge');
  const statusText = statusBadge.querySelector('.status-text');
  
  // Sidebar elements
  const sidebarPanel = document.getElementById('sidebarPanel');
  const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
  const closeSidebarBtn = document.getElementById('closeSidebarBtn');
  const toolsListContainer = document.getElementById('toolsListContainer');
  const sidebarSourcesContainer = document.getElementById('sidebarSourcesContainer');
  const toolsCountBadge = document.getElementById('toolsCountBadge');
  const sourcesCountBadge = document.getElementById('sourcesCountBadge');
  const headerToolCount = document.getElementById('headerToolCount');
  const clearChatBtn = document.getElementById('clearChatBtn');

  // Stats elements
  const statQueries = document.getElementById('statQueries');
  const statTools = document.getElementById('statTools');
  const statSources = document.getElementById('statSources');

  // --- State ---
  const state = {
    messages: [], // In-memory session message history [{ role: 'user'|'assistant', text, tools, sources, timestamp }]
    isGenerating: false,
    totalQueries: 0,
    totalToolCalls: 0,
    totalSources: 0,
    lastTools: [],
    lastSources: []
  };

  // Known tool icon mapping
  const TOOL_ICONS = {
    web_search: '🔍',
    search: '🔍',
    nimble_search: '🔍',
    extract_page: '🌐',
    scrape_url: '📄',
    read_webpage: '📖',
    shop_search: '🛍️',
    extract_product: '🛍️',
    ecommerce: '🛒',
    research_topic: '🔬',
    research: '🔬',
    draft_or_send_email: '✉️',
    email: '✉️',
    summarize: '📝',
    fetch: '🌐',
    default: '⚙️'
  };

  function getToolIcon(toolName) {
    const key = (toolName || '').toLowerCase().replace(/[\s-]/g, '_');
    return TOOL_ICONS[key] || TOOL_ICONS.default;
  }

  // --- Auto-resize Textarea ---
  function adjustTextareaHeight() {
    messageInput.style.height = 'auto';
    const nextHeight = Math.min(messageInput.scrollHeight, 140);
    messageInput.style.height = `${nextHeight}px`;
  }

  messageInput.addEventListener('input', adjustTextareaHeight);

  // --- Voice Input: record in the browser, transcribe with Groq Whisper on the server ---
  // (The Web Speech API only works in Chrome/Edge and fails silently elsewhere.)
  const voiceBtn = document.getElementById('voiceBtn');
  const MAX_RECORDING_MS = 15000;
  let mediaRecorder = null;
  let recordingTimer = null;
  let isListening = false;

  function setStatus(text) {
    statusText.textContent = text;
  }

  function resetVoiceUi() {
    isListening = false;
    voiceBtn.classList.remove('listening');
    statusBadge.classList.remove('status-listening');
    clearTimeout(recordingTimer);
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      setStatus('Mic needs HTTPS or localhost');
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.warn('Microphone permission error:', err);
      setStatus('Mic blocked — allow microphone access');
      return;
    }

    const chunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      resetVoiceUi();
      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
      if (blob.size < 1000) {
        setStatus('Didn\'t catch that — try again');
        return;
      }
      await transcribeAndSend(blob);
    };

    mediaRecorder.start();
    isListening = true;
    voiceBtn.classList.add('listening');
    statusBadge.classList.add('status-listening');
    setStatus('Listening… click mic to stop 🎙️');
    recordingTimer = setTimeout(() => stopRecording(), MAX_RECORDING_MS);
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  }

  async function transcribeAndSend(blob) {
    setStatus('Transcribing…');
    const ext = (blob.type.split('/')[1] || 'webm').split(';')[0];
    const form = new FormData();
    form.append('audio', blob, `speech.${ext}`);
    try {
      const res = await fetch('/api/transcribe', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      if (!data.text) {
        setStatus('Didn\'t catch that — try again');
        return;
      }
      messageInput.value = data.text;
      adjustTextareaHeight();
      state.speakNextReply = true;
      chatForm.dispatchEvent(new Event('submit'));
    } catch (err) {
      console.warn('Transcription error:', err);
      setStatus(`Voice error: ${err.message}`);
    }
  }

  if (voiceBtn) {
    voiceBtn.title = 'Click to speak, click again to send (Groq Whisper)';
    voiceBtn.addEventListener('click', () => {
      if (state.isGenerating) return;
      window.speechSynthesis && window.speechSynthesis.cancel();
      if (replyAudio) replyAudio.pause();
      if (isListening) stopRecording();
      else startRecording();
    });
  }

  // --- Voice Output: read a short version of the reply aloud after a spoken question ---
  // Natural voice (Orpheus TTS via /api/speak) first; browser voice if that's unavailable.
  let replyAudio = null;

  // Show the exact words being spoken at the top of the reply bubble, so voice and text match
  function showSpokenLine(row, text) {
    const bubble = row && row.querySelector('.message-bubble');
    if (!bubble || !text) return;
    const line = document.createElement('div');
    line.className = 'spoken-line';
    line.textContent = `🔊 ${text}`;
    bubble.insertBefore(line, bubble.querySelector('.markdown-body'));
    scrollToBottom();
  }

  async function speakReply(markdown, row) {
    if (replyAudio) replyAudio.pause();
    window.speechSynthesis && window.speechSynthesis.cancel();
    try {
      const res = await fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: markdown })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      replyAudio = new Audio(`data:${data.mime};base64,${data.audio}`);
      showSpokenLine(row, data.text);
      await replyAudio.play();
    } catch (err) {
      console.warn('Natural voice unavailable, using browser voice:', err.message);
      showSpokenLine(row, speakWithBrowser(markdown));
    }
  }

  function speakWithBrowser(markdown) {
    if (!window.speechSynthesis) return '';
    const plain = markdown
      .replace(/```[\s\S]*?```/g, ' ')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/^\|.*\|$/gm, ' ')
      .replace(/^-{3,}$/gm, ' ')
      .replace(/[#*_`>|]/g, '')
      .replace(/\[\d+\]/g, '')
      .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
      .replace(/\s+/g, ' ')
      .trim();
    const sentences = plain.match(/[^.!?]+[.!?]+/g) || [plain];
    const summary = sentences.slice(0, 3).join(' ').slice(0, 400);
    if (!summary) return '';
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(summary);
    utterance.rate = 1.05;
    window.speechSynthesis.speak(utterance);
    return summary;
  }

  // Enter to send, Shift+Enter for newline
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!state.isGenerating && messageInput.value.trim()) {
        chatForm.dispatchEvent(new Event('submit'));
      }
    }
  });

  // --- Quick-Action Buttons ---
  document.querySelectorAll('.quick-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt && !state.isGenerating) {
        messageInput.value = prompt;
        adjustTextareaHeight();
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  // --- Sidebar Toggle ---
  function toggleSidebar() {
    sidebarPanel.classList.toggle('collapsed');
  }

  toggleSidebarBtn.addEventListener('click', toggleSidebar);
  closeSidebarBtn.addEventListener('click', () => {
    sidebarPanel.classList.add('collapsed');
  });

  // --- Clear Chat ---
  clearChatBtn.addEventListener('click', () => {
    if (confirm('Clear the conversation history?')) {
      state.messages = [];
      chatMessages.innerHTML = '';
      if (welcomeCard) {
        chatMessages.appendChild(welcomeCard);
        welcomeCard.style.display = 'block';
      }
      resetInspector();
    }
  });

  function resetInspector() {
    toolsListContainer.innerHTML = `
      <div class="empty-inspector-state">
        <span class="empty-icon">⚡</span>
        <p>No tools executed yet. Ask a query to inspect live web calls!</p>
      </div>`;
    sidebarSourcesContainer.innerHTML = `
      <div class="empty-inspector-state">
        <span class="empty-icon">🔗</span>
        <p>Discovered web URLs and citations will appear here.</p>
      </div>`;
    toolsCountBadge.textContent = '0';
    sourcesCountBadge.textContent = '0';
    headerToolCount.textContent = '0';
  }

  // --- Markdown Parser (Sanitized & Safe) ---
  function parseMarkdown(raw) {
    if (!raw) return '';
    let text = raw;

    // Escape HTML tags to prevent XSS
    text = text.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;');

    // Fenced Code Blocks: ```code```
    text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline Code: `code`
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold + Italic: ***text***
    text = text.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');

    // Bold: **text** or __text__
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>');

    // Italic: *text* or _text_
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    text = text.replace(/_([^_]+)_/g, '<em>$1</em>');

    // Markdown Links: [title](url)
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Auto-link naked URLs not already inside quotes/href
    const nakedUrlRegex = /(?<!href=")(https?:\/\/[^\s<]+)/g;
    text = text.replace(nakedUrlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');

    // Line-by-line block processing: Headers, Lists, Paragraphs
    const lines = text.split('\n');
    let output = [];
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];

      // Headers (###, ##, #)
      if (/^###\s+(.*)/.test(line)) {
        if (inList) { output.push('</ul>'); inList = false; }
        output.push(`<h3>${line.replace(/^###\s+/, '')}</h3>`);
        continue;
      }
      if (/^##\s+(.*)/.test(line)) {
        if (inList) { output.push('</ul>'); inList = false; }
        output.push(`<h2>${line.replace(/^##\s+/, '')}</h2>`);
        continue;
      }
      if (/^#\s+(.*)/.test(line)) {
        if (inList) { output.push('</ul>'); inList = false; }
        output.push(`<h1>${line.replace(/^#\s+/, '')}</h1>`);
        continue;
      }

      // Bullet lists (- or *)
      if (/^\s*[-*]\s+(.*)/.test(line)) {
        if (!inList) {
          output.push('<ul>');
          inList = true;
        }
        output.push(`<li>${line.replace(/^\s*[-*]\s+/, '')}</li>`);
        continue;
      } else {
        if (inList) {
          output.push('</ul>');
          inList = false;
        }
      }

      // Pre blocks or empty lines
      if (line.trim().startsWith('<pre>') || line.trim().startsWith('</pre>') || line.trim().startsWith('<code>')) {
        output.push(line);
      } else if (line.trim().length > 0) {
        output.push(`<p>${line}</p>`);
      }
    }

    if (inList) {
      output.push('</ul>');
    }

    return output.join('');
  }

  // --- Scroll to Bottom ---
  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // --- Render Message Bubble ---
  function appendUserMessage(text) {
    if (welcomeCard) welcomeCard.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'message-row user';

    row.innerHTML = `
      <div class="message-avatar user">You</div>
      <div class="message-content-wrapper">
        <div class="message-bubble">${escapeHtml(text)}</div>
      </div>
    `;

    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendAssistantMessage(data) {
    if (welcomeCard) welcomeCard.style.display = 'none';

    const { response, tools_used = [], sources = [] } = data;
    const row = document.createElement('div');
    row.className = 'message-row assistant';

    // Inline tool chips badge
    let toolsMarkup = '';
    if (tools_used && tools_used.length > 0) {
      const tags = tools_used.map(t => {
        const name = typeof t === 'string' ? t : (t.tool || 'tool');
        return `<span class="tool-tag">${getToolIcon(name)} ${escapeHtml(name)}</span>`;
      }).join('');
      toolsMarkup = `
        <div class="tools-inline-badge">
          <span>Executed:</span> ${tags}
        </div>
      `;
    }

    // Inline sources preview cards
    let sourcesMarkup = '';
    if (sources && sources.length > 0) {
      const sourceCards = sources.map(s => {
        const title = s.title || s.url || 'Web Source';
        const url = s.url || '#';
        const hostname = getHostname(url);
        return `
          <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="source-card" title="${escapeHtml(title)} - ${escapeHtml(url)}">
            <span class="source-favicon">🌐</span>
            <span class="source-title">${escapeHtml(title)}</span>
          </a>
        `;
      }).join('');

      sourcesMarkup = `
        <div class="sources-container">
          <div class="sources-header">
            <span>Sources & Citations (${sources.length})</span>
          </div>
          <div class="sources-grid">
            ${sourceCards}
          </div>
        </div>
      `;
    }

    const parsedContent = parseMarkdown(response || 'No response received.');

    row.innerHTML = `
      <div class="message-avatar assistant">
        <img src="favicon.svg" alt="Nimble Buddy AI">
      </div>
      <div class="message-content-wrapper">
        <div class="message-bubble">
          ${toolsMarkup}
          <div class="markdown-body">${parsedContent}</div>
          ${sourcesMarkup}
        </div>
      </div>
    `;

    chatMessages.appendChild(row);
    scrollToBottom();
    return row;
  }

  // --- Typing Indicator ---
  let currentTypingRow = null;

  function showTypingIndicator() {
    if (welcomeCard) welcomeCard.style.display = 'none';

    currentTypingRow = document.createElement('div');
    currentTypingRow.className = 'typing-indicator-row';
    currentTypingRow.innerHTML = `
      <div class="message-avatar assistant">
        <img src="favicon.svg" alt="Nimble Buddy AI">
      </div>
      <div class="typing-bubble">
        <div class="typing-dots">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
        <span class="typing-text">Nimble is browsing & thinking...</span>
      </div>
    `;

    chatMessages.appendChild(currentTypingRow);
    scrollToBottom();

    // Update status badge
    statusBadge.classList.add('working');
    statusText.textContent = 'Browsing Live Web...';
  }

  function hideTypingIndicator() {
    if (currentTypingRow) {
      currentTypingRow.remove();
      currentTypingRow = null;
    }
    statusBadge.classList.remove('working');
    statusText.textContent = 'Ready';
  }

  // --- Inspector Panel Updater ---
  function updateInspector(toolsUsed = [], sources = []) {
    state.lastTools = toolsUsed;
    state.lastSources = sources;

    // Update tools panel
    toolsCountBadge.textContent = toolsUsed.length.toString();
    headerToolCount.textContent = toolsUsed.length.toString();

    if (toolsUsed.length > 0) {
      toolsListContainer.innerHTML = toolsUsed.map(t => {
        const name = typeof t === 'string' ? t : (t.tool || 'tool');
        const params = (typeof t === 'object' && t.params) ? Object.entries(t.params).map(([k, v]) => `${k}: ${v}`).join(' · ') : '';
        return `
          <div class="tool-item">
            <span class="tool-item-icon">${getToolIcon(name)}</span>
            <div class="tool-item-info">
              <span class="tool-item-name">${escapeHtml(name)}</span>
              ${params ? `<span class="tool-item-params" style="font-size:0.75rem; color:var(--text-subtle); display:block;">${escapeHtml(params)}</span>` : ''}
              <span class="tool-item-status">✓ Completed</span>
            </div>
          </div>
        `;
      }).join('');
    } else {
      toolsListContainer.innerHTML = `
        <div class="empty-inspector-state">
          <span class="empty-icon">ℹ️</span>
          <p>No tools were required for this answer.</p>
        </div>
      `;
    }

    // Update sources panel
    sourcesCountBadge.textContent = sources.length.toString();
    if (sources.length > 0) {
      sidebarSourcesContainer.innerHTML = sources.map(s => {
        const title = s.title || 'Untitled Source';
        const url = s.url || '#';
        const domain = getHostname(url);
        return `
          <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="sidebar-source-link">
            <span class="sidebar-source-title">${escapeHtml(title)}</span>
            <span class="sidebar-source-domain">${escapeHtml(domain)}</span>
          </a>
        `;
      }).join('');
    } else {
      sidebarSourcesContainer.innerHTML = `
        <div class="empty-inspector-state">
          <span class="empty-icon">🔍</span>
          <p>No specific external URLs cited.</p>
        </div>
      `;
    }

    // Update session stats
    statQueries.textContent = state.totalQueries.toString();
    statTools.textContent = state.totalToolCalls.toString();
    statSources.textContent = state.totalSources.toString();
  }

  // --- Send Message Handler ---
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (state.isGenerating) return;

    const userText = messageInput.value.trim();
    if (!userText) return;

    // Add user message to UI
    appendUserMessage(userText);
    state.messages.push({ role: 'user', text: userText, timestamp: Date.now() });
    state.totalQueries += 1;
    statQueries.textContent = state.totalQueries.toString();

    // Reset input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;
    state.isGenerating = true;

    showTypingIndicator();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        // Send recent turns so follow-ups like "email that summary" have context
        body: JSON.stringify({
          message: userText,
          history: state.messages
            .slice(0, -1)
            .filter(m => m.text)
            .slice(-6)
            .map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text.slice(0, 3000) }))
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      hideTypingIndicator();

      // Normalize data structure
      const aiResponse = data.response || data.message || 'I have completed your request.';
      const toolsUsed = Array.isArray(data.tools_used) ? data.tools_used : [];
      const sources = Array.isArray(data.sources) ? data.sources : [];

      // Update state stats
      state.totalToolCalls += toolsUsed.length;
      state.totalSources += sources.length;

      // Render assistant message
      const assistantRow = appendAssistantMessage({
        response: aiResponse,
        tools_used: toolsUsed,
        sources: sources
      });

      state.messages.push({
        role: 'assistant',
        text: aiResponse,
        tools: toolsUsed,
        sources: sources,
        timestamp: Date.now()
      });

      // Update inspector sidebar
      updateInspector(toolsUsed, sources);

      if (state.speakNextReply) speakReply(aiResponse, assistantRow);

    } catch (err) {
      console.error('Chat error:', err);
      hideTypingIndicator();

      appendAssistantMessage({
        response: `⚠️ **Connection Error**: Unable to reach \`/api/chat\` (${err.message}).\n\nPlease ensure the FastAPI server is running with the Nimble backend configured!`,
        tools_used: [],
        sources: []
      });
    } finally {
      state.speakNextReply = false;
      state.isGenerating = false;
      sendBtn.disabled = false;
      messageInput.focus();
    }
  });

  // --- Helpers ---
  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function getHostname(url) {
    try {
      const parsed = new URL(url);
      return parsed.hostname.replace(/^www\./, '');
    } catch {
      return url || '';
    }
  }
});
