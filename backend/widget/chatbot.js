/**
 * Customer Support Chatbot Widget
 * Drop this script + styles.css into any website.
 *
 * Config is fetched from /api/config — set env vars in Railway.
 */
(function () {
  "use strict";

  // ── Configuration (defaults, overridden by /api/config) ────────
  const CONFIG = {
    apiUrl: "https://websitechatbot-production-0f7c.up.railway.app",
    companyName: "MAAN AI",
    welcomeMessage: "👋 Hi there! I'm your AI support assistant. How can I help you today?",
    suggestions: [
      "What are your business hours?",
      "Do you offer a free trial?",
      "How do I reset my password?",
      "What's your refund policy?",
    ],
    accentColor: "#6C63FF",
    position: "right",
  };

  // ── State ───────────────────────────────────────────────────────
  let sessionId = localStorage.getItem("cb_session") || null;
  let isOpen = false;
  let isTyping = false;
  let messageCount = 0;

  // ── DOM helpers ─────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // ── Init Session ────────────────────────────────────────────────
  async function initSession(forceNew = false) {
    if (sessionId && !forceNew) return;
    try {
      const res = await fetch(`${CONFIG.apiUrl}/api/chat/session`, { method: "POST" });
      const data = await res.json();
      sessionId = data.session_id;
      localStorage.setItem("cb_session", sessionId);
    } catch (e) {
      sessionId = "local-" + Math.random().toString(36).slice(2);
    }
  }

  function startNewChat() {
    sessionId = null;
    localStorage.removeItem("cb_session");
    $("chatbot-messages").innerHTML = "";
    $("chatbot-suggestions").innerHTML = "";
    initSession(true).then(() => {
      appendBotMessage(CONFIG.welcomeMessage);
      if (CONFIG.suggestions?.length) renderSuggestions(CONFIG.suggestions);
    });
  }

  function endChat() {
    sessionId = null;
    localStorage.removeItem("cb_session");
    $("chatbot-messages").innerHTML = "";
    $("chatbot-suggestions").innerHTML = "";
    toggleWidget();
  }

  // ── Widget HTML ─────────────────────────────────────────────────
  function injectHTML() {
    // Launcher button
    const launcher = el(
      "button",
      "",
      `<svg class="icon-chat" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
       </svg>
       <svg class="icon-close" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
       </svg>
       <span class="badge">1</span>`
    );
    launcher.id = "chatbot-launcher";
    launcher.setAttribute("aria-label", "Open chat");
    launcher.addEventListener("click", toggleWidget);

    // Widget
    const widget = el("div", "");
    widget.id = "chatbot-widget";
    widget.innerHTML = `
      <div id="chatbot-header">
        <div class="header-avatar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
          </svg>
        </div>
        <div class="header-info">
          <h3>${CONFIG.companyName} Support</h3>
          <span>● Online · Typically replies instantly</span>
        </div>
        <div class="header-actions">
          <button id="chatbot-new-chat" title="New Chat" aria-label="Start new conversation">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
          </button>
          <button id="chatbot-minimize" title="Minimize" aria-label="Minimize">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>
      </div>

      <div id="chatbot-messages" role="log" aria-live="polite"></div>

      <div id="chatbot-suggestions"></div>

      <div id="chatbot-input-area">
        <textarea
          id="chatbot-input"
          placeholder="Type a message…"
          rows="1"
          maxlength="1000"
          aria-label="Chat message"
        ></textarea>
        <button id="chatbot-send" aria-label="Send">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <div class="powered-by">
        Powered by AI ·
        <button id="chatbot-end" title="End Chat" style="float:right; background:none; border:none; color:inherit; cursor:pointer; font-size:10px; text-decoration:underline; padding:0; margin:0;">End Chat</button>
      </div>
    `;

    document.body.appendChild(launcher);
    document.body.appendChild(widget);

    // Events
    $("chatbot-new-chat").addEventListener("click", startNewChat);
    $("chatbot-minimize").addEventListener("click", toggleWidget);
    $("chatbot-send").addEventListener("click", handleSend);
    $("chatbot-end").addEventListener("click", endChat);
    $("chatbot-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    $("chatbot-input").addEventListener("input", autoResize);

    // Suggestions
    renderSuggestions(CONFIG.suggestions);
  }

  function autoResize() {
    const ta = $("chatbot-input");
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 100) + "px";
  }

  // ── Toggle widget open/close ─────────────────────────────────────
  function toggleWidget() {
    isOpen = !isOpen;
    $("chatbot-widget").classList.toggle("open", isOpen);
    $("chatbot-launcher").classList.toggle("open", isOpen);

    if (isOpen) {
      const badge = document.querySelector("#chatbot-launcher .badge");
      if (badge) badge.style.display = "none";
      setTimeout(() => $("chatbot-input").focus(), 350);
      if (messageCount === 0) {
        appendBotMessage(CONFIG.welcomeMessage);
      }
    }
  }

  // ── Suggestions ──────────────────────────────────────────────────
  function renderSuggestions(items) {
    const container = $("chatbot-suggestions");
    container.innerHTML = "";
    items.forEach((text) => {
      const chip = el("button", "suggestion-chip", text);
      chip.addEventListener("click", () => {
        container.innerHTML = "";
        $("chatbot-input").value = text;
        handleSend();
      });
      container.appendChild(chip);
    });
  }

  // ── Append messages ──────────────────────────────────────────────
  function appendUserMessage(text) {
    const messages = $("chatbot-messages");
    const row = el("div", "msg-row user");
    row.innerHTML = `
      <div class="msg-content">
        <div class="msg-bubble">${escapeHtml(text)}</div>
        <span class="msg-time">${formatTime(new Date())}</span>
      </div>
      <div class="msg-avatar">You</div>
    `;
    messages.appendChild(row);
    scrollToBottom();
    messageCount++;
  }

  function appendBotMessage(text) {
    const messages = $("chatbot-messages");
    const row = el("div", "msg-row bot");
    row.innerHTML = `
      <div class="msg-avatar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
        </svg>
      </div>
      <div class="msg-content">
        <div class="msg-bubble">${formatBotText(text)}</div>
        <span class="msg-time">${formatTime(new Date())}</span>
      </div>
    `;
    messages.appendChild(row);
    scrollToBottom();
    messageCount++;
  }

  function showTypingIndicator() {
    const messages = $("chatbot-messages");
    const row = el("div", "msg-row bot");
    row.id = "typing-row";
    row.innerHTML = `
      <div class="msg-avatar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
        </svg>
      </div>
      <div class="msg-content">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    messages.appendChild(row);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    const row = $("typing-row");
    if (row) row.remove();
  }

  function scrollToBottom() {
    const messages = $("chatbot-messages");
    messages.scrollTop = messages.scrollHeight;
  }

  // ── Send message ─────────────────────────────────────────────────
  async function handleSend() {
    const input = $("chatbot-input");
    const text = input.value.trim();
    if (!text || isTyping) return;

    $("chatbot-suggestions").innerHTML = "";
    input.value = "";
    input.style.height = "auto";
    $("chatbot-send").disabled = true;
    isTyping = true;

    appendUserMessage(text);
    showTypingIndicator();

    await initSession();

    try {
      const res = await fetch(`${CONFIG.apiUrl}/api/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });

      if (!res.ok) throw new Error("API error");

      const data = await res.json();
      removeTypingIndicator();
      appendBotMessage(data.reply);
    } catch (err) {
      removeTypingIndicator();
      appendBotMessage(
        "I'm having trouble connecting right now. Please try again in a moment."
      );
    }

    isTyping = false;
    $("chatbot-send").disabled = false;
    input.focus();
  }

  // ── Utilities ────────────────────────────────────────────────────
  function escapeHtml(text) {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }

  function formatBotText(text) {
    return escapeHtml(text)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  // ── Boot ─────────────────────────────────────────────────────────
  async function boot() {
    // Inject CSS
    if (!document.querySelector("[data-chatbot-css]")) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = CONFIG.cssUrl || "styles.css";
      link.setAttribute("data-chatbot-css", "1");
      document.head.appendChild(link);
    }

    // Fetch config from backend (Railway env vars live here, never exposed to browser)
    try {
      const res = await fetch(`${CONFIG.apiUrl}/api/config`);
      if (res.ok) {
        const remote = await res.json();
        // Only override safe display fields — never apiUrl
        if (remote.companyName)    CONFIG.companyName    = remote.companyName;
        if (remote.welcomeMessage) CONFIG.welcomeMessage = remote.welcomeMessage;
        if (remote.accentColor)    CONFIG.accentColor    = remote.accentColor;
        if (remote.suggestions)    CONFIG.suggestions    = remote.suggestions;
      }
    } catch (e) {
      // Silently fall back to defaults
    }

    injectHTML();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
