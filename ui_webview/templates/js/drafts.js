/* ==========================================================================
   drafts.js  –  Drafts tab logic
   ========================================================================== */

// ── Load & Render ─────────────────────────────────────────────────────────
async function loadDrafts() {
    const res = await pywebview.api.get_drafts();
    const list = document.getElementById('drafts-list');
    if (!list) return;

    if (!res.success || !res.drafts.length) {
        list.innerHTML = `
            <div style="text-align:center;padding:48px;color:var(--text-secondary);">
                <div style="font-size:40px;margin-bottom:12px;">📭</div>
                <p>No drafts yet. Use the <b>AI Chat</b> or <b>Single Email</b> tab to create drafts.</p>
            </div>`;
        return;
    }
    list.innerHTML = res.drafts.map(d => draftCard(d)).join('');
    bindDraftCardEvents();
}

function draftCard(d) {
    const preview = (d.body || '').slice(0, 140).replace(/\n/g, ' ');
    const attCount = (d.attachments || []).length;
    const sourceIcon = d.source === 'chat' ? '💬' : d.source === 'bulk' ? '📦' : '✏️';
    return `
    <div class="draft-card" id="draft-card-${d.id}" data-draft-id="${d.id}">
        <div class="draft-card-header">
            <div>
                <span class="draft-source-badge">${sourceIcon} ${d.source}</span>
                <span class="draft-date">${d.created_at.slice(0,16).replace('T',' ')}</span>
            </div>
            <div class="draft-card-actions">
                <button class="btn btn-sm btn-secondary draft-btn-attach" data-id="${d.id}" title="Add attachment">📎</button>
                <button class="btn btn-sm btn-secondary draft-btn-edit" data-id="${d.id}">✏️ Edit</button>
                <button class="btn btn-sm btn-primary draft-btn-send" data-id="${d.id}">📤 Send</button>
                <button class="btn btn-sm btn-secondary draft-btn-delete" data-id="${d.id}" style="color:var(--danger-color)">🗑</button>
            </div>
        </div>
        <div class="draft-to"><b>To:</b> ${escapeHtml(d.to || '—')}</div>
        <div class="draft-subject"><b>Subject:</b> ${escapeHtml(d.subject || 'No subject')}</div>
        <div class="draft-preview">${escapeHtml(preview)}${d.body.length > 140 ? '…' : ''}</div>
        ${attCount ? `<div class="draft-attachments">📎 ${attCount} attachment${attCount > 1 ? 's' : ''}: ${(d.attachments || []).map(a => escapeHtml(a.split(/[\\/]/).pop())).join(', ')}</div>` : ''}
    </div>`;
}

function bindDraftCardEvents() {
    document.querySelectorAll('.draft-btn-edit').forEach(btn => {
        btn.addEventListener('click', () => openDraftEditor(btn.dataset.id));
    });
    document.querySelectorAll('.draft-btn-send').forEach(btn => {
        btn.addEventListener('click', () => sendDraftById(btn.dataset.id));
    });
    document.querySelectorAll('.draft-btn-delete').forEach(btn => {
        btn.addEventListener('click', () => deleteDraftById(btn.dataset.id));
    });
    document.querySelectorAll('.draft-btn-attach').forEach(btn => {
        btn.addEventListener('click', () => addAttachmentToDraft(btn.dataset.id));
    });
}

// ── Highlight a specific draft ─────────────────────────────────────────────
function highlightDraft(draftId) {
    const card = document.getElementById('draft-card-' + draftId);
    if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.add('draft-highlight');
        setTimeout(() => card.classList.remove('draft-highlight'), 2000);
    }
}

// ── Edit ──────────────────────────────────────────────────────────────────
function openDraftEditor(draftId) {
    const modal = document.getElementById('draft-edit-modal');
    if (!modal) return;

    const res_cache = _draftCache[draftId];
    if (!res_cache) { loadDraftIntoEditor(draftId); return; }
    _populateDraftEditor(res_cache);
    modal.classList.add('active');
}

const _draftCache = {};

async function loadDraftIntoEditor(draftId) {
    const res = await pywebview.api.get_drafts();
    if (!res.success) return;
    const draft = (res.drafts || []).find(d => d.id === draftId);
    if (!draft) return;
    _draftCache[draftId] = draft;
    _populateDraftEditor(draft);
    document.getElementById('draft-edit-modal').classList.add('active');
}

function _populateDraftEditor(draft) {
    setVal('draft-edit-id',      draft.id);
    setVal('draft-edit-to',      draft.to);
    setVal('draft-edit-subject', draft.subject);
    setVal('draft-edit-body',    draft.body);
}

async function saveDraftEdit() {
    const id = getVal('draft-edit-id');
    if (!id) return;
    const res = await pywebview.api.update_draft({
        id:      id,
        to:      getVal('draft-edit-to'),
        subject: getVal('draft-edit-subject'),
        body:    getVal('draft-edit-body'),
    });
    document.getElementById('draft-edit-modal').classList.remove('active');
    if (res.success) {
        await loadDrafts();
        showFlash('flash-drafts', '✔ Draft updated');
    } else {
        showFlash('flash-drafts', '✘ ' + res.error, true);
    }
}

// ── Send ──────────────────────────────────────────────────────────────────
async function sendDraftById(draftId) {
    if (!confirm('Send this draft now?')) return;
    const btn = document.querySelector(`.draft-btn-send[data-id="${draftId}"]`);
    if (btn) { btn.disabled = true; btn.innerText = 'Sending…'; }
    const res = await pywebview.api.send_draft({ draft_id: draftId });
    if (btn) { btn.disabled = false; btn.innerText = '📤 Send'; }
    if (res.success) {
        showFlash('flash-drafts', '✔ Email sent!');
        await loadDrafts();
    } else {
        showFlash('flash-drafts', '✘ ' + (res.error || 'Send failed'), true);
    }
}

// ── Delete ────────────────────────────────────────────────────────────────
async function deleteDraftById(draftId) {
    if (!confirm('Delete this draft?')) return;
    await pywebview.api.delete_draft({ id: draftId });
    await loadDrafts();
}

// ── Attachments ───────────────────────────────────────────────────────────
async function addAttachmentToDraft(draftId) {
    const res = await pywebview.api.pick_attachment();
    if (!res.success || !res.files.length) return;

    // Load current draft
    const draftsRes = await pywebview.api.get_drafts();
    if (!draftsRes.success) return;
    const draft = (draftsRes.drafts || []).find(d => d.id === draftId);
    if (!draft) return;

    const existing = draft.attachments || [];
    const newAtts  = [...new Set([...existing, ...res.files])];
    await pywebview.api.update_draft({ id: draftId, attachments: newAtts });
    showFlash('flash-drafts', `✔ ${res.files.length} file(s) attached`);
    await loadDrafts();
}

// ── Quick-create draft from Single Email tab ──────────────────────────────
async function saveCurrentDraft(to, subject, body) {
    const res = await pywebview.api.create_draft({ to, subject, body, source: 'manual' });
    return res;
}

// ── Bind events ────────────────────────────────────────────────────────────
function bindDraftEvents() {
    const saveBtn = document.getElementById('btn-save-draft-edit');
    if (saveBtn) saveBtn.addEventListener('click', saveDraftEdit);

    const cancelBtn = document.getElementById('btn-cancel-draft-edit');
    if (cancelBtn) cancelBtn.addEventListener('click', () => {
        document.getElementById('draft-edit-modal').classList.remove('active');
    });

    const modal = document.getElementById('draft-edit-modal');
    if (modal) modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.remove('active');
    });
}
