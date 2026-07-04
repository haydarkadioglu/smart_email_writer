/* ==========================================================================
   chat.js  –  AI Chat tab logic
   ========================================================================== */

let activeChatSessionId      = null;
let activeChatAttachmentPaths = [];   // [{path, name}]

// ── Init ──────────────────────────────────────────────────────────────────
async function initChatTab() {
    await loadChatSessions();
    // Auto-create a session if none
    const sessionsEl = document.getElementById('chat-sessions-list');
    if (sessionsEl && sessionsEl.children.length === 0) {
        await newChatSession();
    }
}

// ── Session management ─────────────────────────────────────────────────────
async function loadChatSessions() {
    const res = await pywebview.api.chat_get_sessions();
    const list = document.getElementById('chat-sessions-list');
    if (!list || !res.success) return;

    if (!res.sessions.length) {
        list.innerHTML = '<p style="color:var(--text-secondary);font-size:12px;padding:8px 0;">No chats yet</p>';
        return;
    }
    list.innerHTML = res.sessions.map(s => `
        <div class="chat-session-item ${s.id === activeChatSessionId ? 'active' : ''}"
             data-sid="${s.id}" onclick="switchChatSession('${s.id}')">
            <div class="chat-session-title">${escapeHtml(s.title)}</div>
            <div class="chat-session-meta">${s.msg_count} msg · ${s.updated_at.slice(0,10)}</div>
        </div>
    `).join('');
}

async function newChatSession() {
    const res = await pywebview.api.chat_new_session();
    if (!res.success) return;
    activeChatSessionId = res.session.id;
    await loadChatSessions();
    clearChatMessages();
}

async function switchChatSession(sessionId) {
    activeChatSessionId = sessionId;
    const res = await pywebview.api.chat_get_session({ session_id: sessionId });
    if (!res.success) return;
    await loadChatSessions(); // refresh highlights
    renderChatHistory(res.session.messages || []);
}

async function deleteChatSession(sessionId) {
    if (!confirm('Delete this chat session?')) return;
    await pywebview.api.chat_delete_session({ session_id: sessionId });
    if (activeChatSessionId === sessionId) {
        activeChatSessionId = null;
        clearChatMessages();
    }
    await loadChatSessions();
}

function clearChatMessages() {
    const el = document.getElementById('chat-messages');
    if (el) el.innerHTML = `
        <div class="chat-welcome">
            <div style="font-size:36px;margin-bottom:8px;">🤖</div>
            <h3 style="margin:0 0 8px;">SEW AI</h3>
            <p style="color:var(--text-secondary);font-size:13px;">
                Ask me to draft an email, prepare a list of emails for multiple recipients, 
                or ask for advice on your message.
            </p>
        </div>`;
}

function renderChatHistory(messages) {
    const el = document.getElementById('chat-messages');
    if (!el) return;
    if (!messages.length) { clearChatMessages(); return; }
    el.innerHTML = messages.map(m => chatBubble(m.role, m.content, m.draft_ids)).join('');
    el.scrollTop = el.scrollHeight;
}

// ── Sending ───────────────────────────────────────────────────────────────
async function attachFileToChat() {
    const res = await pywebview.api.pick_files({
        multiple: true,
        file_types: ['.pdf', '.docx', '.txt', '.md', '.csv', '.xlsx', '.xls', '.png', '.jpg']
    });
    if (!res || !res.length) return;

    const paths = Array.isArray(res) ? res : [res];
    paths.forEach(file_path => {
        if (activeChatAttachmentPaths.some(a => a.path === file_path)) return; // no duplicates
        const parts = file_path.split(/[/\\]/);
        activeChatAttachmentPaths.push({ path: file_path, name: parts[parts.length - 1] });
    });
    renderChatAttachmentPreview();
}

function renderChatAttachmentPreview() {
    const preview = document.getElementById('chat-attachment-preview');
    if (!preview) return;
    if (!activeChatAttachmentPaths.length) {
        preview.style.display = 'none';
        preview.innerHTML = '';
        return;
    }
    preview.style.display = 'flex';
    preview.innerHTML = activeChatAttachmentPaths.map((a, i) => `
        <span style="display:inline-flex;align-items:center;gap:4px;background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:4px;padding:2px 8px;font-size:12px;">
            📎 ${escapeHtml(a.name)}
            <span onclick="removeChatAttachment(${i})" style="cursor:pointer;color:var(--danger-color);font-weight:bold;margin-left:4px;">✕</span>
        </span>`).join('');
}

function removeChatAttachment(idx) {
    activeChatAttachmentPaths.splice(idx, 1);
    renderChatAttachmentPreview();
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const msg = input?.value?.trim();
    
    // Allow sending if there is either a text message or an attachment
    if (!msg && !activeChatAttachmentPaths.length) return;

    if (!activeChatSessionId) {
        const res = await pywebview.api.chat_new_session();
        if (!res.success) return;
        activeChatSessionId = res.session.id;
    }

    const saveAsDraft   = document.getElementById('chat-save-as-draft')?.checked ?? true;
    const attachments   = [...activeChatAttachmentPaths];

    // Build user message display
    let displayedMsg = msg || '';
    if (attachments.length) {
        const names = attachments.map(a => a.name).join(', ');
        displayedMsg = `📎 [Attached: ${names}]` + (msg ? `\n${msg}` : '');
    }

    appendChatBubble('user', displayedMsg);
    
    // Clear input and attachments
    if (input) {
        input.value = '';
        input.style.height = 'auto';
    }
    activeChatAttachmentPaths = [];
    renderChatAttachmentPreview();

    // Typing indicator
    const typingId = 'typing-' + Date.now();
    appendTypingIndicator(typingId);

    const res = await pywebview.api.chat_send_message({
        session_id:       activeChatSessionId,
        message:          msg || '',
        save_as_draft:    saveAsDraft,
        attachment_paths: attachments.map(a => a.path),
    });

    removeTypingIndicator(typingId);

    // The streaming bubble is created by Python via evaluate_js during the call.
    // When the API returns, finalize it (add draft badges, handle plain-text format).
    if (!res.success) {
        appendChatBubble('assistant', '⚠ Error: ' + res.error);
        await loadChatSessions();
        return;
    }

    finalizeStreamingBubble(res.stream_id, res.message, res.draft_ids);
    if (res.draft_ids && res.draft_ids.length > 0) {
        showFlash('flash-chat', `✔ ${res.draft_ids.length} draft(s) saved`, false);
    }

    // ── Auto-continue for large batch generation ─────────────────────────
    if (res.continuation_needed) {
        let totalDrafts = res.draft_ids ? res.draft_ids.length : 0;
        let keepGoing   = true;

        while (keepGoing) {
            const contTypingId = 'typing-' + Date.now();
            appendTypingIndicator(contTypingId);

            const cont = await pywebview.api.chat_continue_generation({
                session_id:    activeChatSessionId,
                save_as_draft: saveAsDraft,
                already_count: totalDrafts,
            });

            removeTypingIndicator(contTypingId);

            if (!cont.success) {
                appendChatBubble('assistant', '⚠ Continue error: ' + cont.error);
                break;
            }

            appendChatBubble('assistant', cont.message, cont.draft_ids);
            if (cont.draft_ids && cont.draft_ids.length > 0) {
                totalDrafts += cont.draft_ids.length;
                showFlash('flash-chat', `✔ ${totalDrafts} total draft(s) saved`, false);
            }

            keepGoing = !!cont.continuation_needed;
        }
    }

    await loadChatSessions(); // refresh titles
}

function appendChatBubble(role, content, draftIds) {
    const el = document.getElementById('chat-messages');
    if (!el) return;
    // Remove welcome screen if present
    const welcome = el.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
    el.insertAdjacentHTML('beforeend', chatBubble(role, content, draftIds));
    el.scrollTop = el.scrollHeight;
}

function chatBubble(role, content, draftIds) {
    const isUser = role === 'user';
    const draftBadges = (draftIds && draftIds.length)
        ? `<div class="chat-draft-badges">${draftIds.map(id => `
            <button class="chat-draft-badge" onclick="openDraftFromChat('${id}')">
                📋 View Draft
            </button>`).join('')}
           </div>`
        : '';
    return `
    <div class="chat-bubble ${isUser ? 'chat-bubble-user' : 'chat-bubble-ai'}">
        <div class="chat-bubble-content">${escapeHtml(content).replace(/\n/g,'<br>')}</div>
        ${draftBadges}
    </div>`;
}

function appendTypingIndicator(id) {
    const el = document.getElementById('chat-messages');
    if (!el) return;
    el.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="chat-bubble chat-bubble-ai">
            <div class="chat-typing-dots">
                <span></span><span></span><span></span>
            </div>
        </div>`);
    el.scrollTop = el.scrollHeight;
}

function removeTypingIndicator(id) {
    document.getElementById(id)?.remove();
}

// ── Streaming bubble helpers ──────────────────────────────────────────────
function createStreamingBubble(streamId) {
    const el = document.getElementById('chat-messages');
    if (!el) return;
    // Remove welcome screen if present
    const welcome = el.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
    // Remove existing typing indicators
    el.querySelectorAll('.chat-typing-dots').forEach(d => d.closest('.chat-bubble')?.remove());

    el.insertAdjacentHTML('beforeend', `
        <div id="${streamId}" class="chat-bubble chat-bubble-ai">
            <div class="chat-bubble-content stream-content" style="white-space:pre-wrap;"></div>
            <span class="stream-cursor">▋</span>
        </div>`);
    el.scrollTop = el.scrollHeight;
}

function appendChatStreamChunk(streamId, text) {
    const bubble = document.getElementById(streamId);
    if (!bubble) return;
    const content = bubble.querySelector('.stream-content');
    if (content) {
        content.textContent += text;
    }
    const el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
}

function finalizeStreamingBubble(streamId, finalMessage, draftIds) {
    const bubble = streamId ? document.getElementById(streamId) : null;
    if (!bubble) {
        // Fallback: no streaming bubble found, just append normally
        appendChatBubble('assistant', finalMessage || '', draftIds);
        return;
    }
    // Remove blinking cursor
    bubble.querySelector('.stream-cursor')?.remove();

    // Replace raw streamed text with properly formatted final message
    const content = bubble.querySelector('.stream-content');
    if (content && finalMessage) {
        content.innerHTML = escapeHtml(finalMessage).replace(/\n/g, '<br>');
    }

    // Add draft badges if present
    if (draftIds && draftIds.length) {
        const badges = document.createElement('div');
        badges.className = 'chat-draft-badges';
        badges.innerHTML = draftIds.map(id => `
            <button class="chat-draft-badge" onclick="openDraftFromChat('${id}')">
                📋 View Draft
            </button>`).join('');
        bubble.appendChild(badges);
    }

    const el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
}

function openDraftFromChat(draftId) {
    switchTab('drafts');
    // Highlight the draft after tab switches
    setTimeout(() => highlightDraft(draftId), 300);
}

// ── Bind events ────────────────────────────────────────────────────────────
function bindChatEvents() {
    const sendBtn = document.getElementById('btn-chat-send');
    if (sendBtn) sendBtn.addEventListener('click', sendChatMessage);

    const attachBtn = document.getElementById('btn-chat-attach');
    if (attachBtn) attachBtn.addEventListener('click', attachFileToChat);

    const removeAttachBtn = document.getElementById('btn-chat-remove-attachment');
    if (removeAttachBtn) removeAttachBtn.addEventListener('click', removeChatAttachment);

    const input = document.getElementById('chat-input');
    if (input) {
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 140) + 'px';
        });
    }

    const newBtn = document.getElementById('btn-chat-new');
    if (newBtn) newBtn.addEventListener('click', newChatSession);
}
