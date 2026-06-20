/* ==========================================================================
   single_email.js  –  Single Email tab logic
   ========================================================================== */

// ── Undo/Redo Stack ───────────────────────────────────────────────────────
const editorHistory = [];      // stack of {subject, draft} snapshots
let   editorHistoryIdx = -1;   // current position in the stack
const MAX_HISTORY = 50;

function pushEditorSnapshot() {
    const snap = {
        subject: getVal('email-subject'),
        draft:   getVal('draft-output'),
    };
    // Trim future states if user typed after undo
    editorHistory.splice(editorHistoryIdx + 1);
    editorHistory.push(snap);
    if (editorHistory.length > MAX_HISTORY) editorHistory.shift();
    editorHistoryIdx = editorHistory.length - 1;
    updateUndoRedoBtns();
}

function updateUndoRedoBtns() {
    const undoBtn = document.getElementById('btn-undo');
    const redoBtn = document.getElementById('btn-redo');
    if (undoBtn) undoBtn.disabled = editorHistoryIdx <= 0;
    if (redoBtn) redoBtn.disabled = editorHistoryIdx >= editorHistory.length - 1;
}

function handleUndo() {
    if (editorHistoryIdx <= 0) return;
    editorHistoryIdx--;
    const snap = editorHistory[editorHistoryIdx];
    document.getElementById('draft-output').value  = snap.draft;
    document.getElementById('email-subject').value = snap.subject;
    updateUndoRedoBtns();
    runEditorAnalysis();
}

function handleRedo() {
    if (editorHistoryIdx >= editorHistory.length - 1) return;
    editorHistoryIdx++;
    const snap = editorHistory[editorHistoryIdx];
    document.getElementById('draft-output').value  = snap.draft;
    document.getElementById('email-subject').value = snap.subject;
    updateUndoRedoBtns();
    runEditorAnalysis();
}

const DEFAULT_PROMPT_TEMPLATES = [
    { id: "collab", title: "Collaboration / Discovery Call", prompt: "Schedule a brief 10-minute discovery call to discuss potential collaboration and partnership opportunities." },
    { id: "job", title: "Job Application / CV Outreach", prompt: "Reach out to express interest in open positions and discuss how my skills and experience align with the team's needs." },
    { id: "followup", title: "Meeting Follow-Up", prompt: "Follow up regarding our recent conversation, summarize the key points we discussed, and schedule a next meeting to align on next steps." }
];

function getSavedPromptTemplates() {
    if (appConfig && appConfig.settings && appConfig.settings.prompt_templates) {
        return appConfig.settings.prompt_templates;
    }
    return DEFAULT_PROMPT_TEMPLATES;
}

function updateSinglePromptTemplateDropdown() {
    const selector = document.getElementById('single-prompt-template');
    if (!selector) return;
    const val = selector.value;
    const list = getSavedPromptTemplates();
    let html = `<option value="custom">Custom (Type below)</option>`;
    list.forEach(t => {
        html += `<option value="${t.id}">${escapeHtml(t.title)}</option>`;
    });
    selector.innerHTML = html;
    if (list.some(t => t.id === val)) {
        selector.value = val;
    } else {
        selector.value = 'custom';
    }
}

function initPurposeModal() {
    const modal = document.getElementById('purpose-modal');
    const preview = document.getElementById('single-purpose-preview');
    const btnEdit = document.getElementById('btn-edit-purpose');
    const btnClose = document.getElementById('btn-close-purpose-modal');
    const btnCancel = document.getElementById('btn-cancel-purpose-modal');
    const btnSave = document.getElementById('btn-save-purpose-modal');
    const textarea = document.getElementById('modal-purpose-textarea');
    const hiddenInput = document.getElementById('single-purpose');

    function openModal() {
        textarea.value = hiddenInput.value;
        modal.classList.add('active');
        textarea.focus();
    }

    function closeModal() {
        modal.classList.remove('active');
    }

    function saveValue() {
        const val = textarea.value;
        hiddenInput.value = val;
        
        if (val.trim()) {
            preview.innerText = val.trim();
            preview.style.color = 'var(--text-primary)';
        } else {
            preview.innerText = '(No details entered)';
            preview.style.color = 'var(--text-secondary)';
        }

        const currentTemplateVal = document.getElementById('single-prompt-template').value;
        if (currentTemplateVal !== 'custom') {
            const templates = getSavedPromptTemplates();
            const currentTemplate = templates.find(t => t.id === currentTemplateVal);
            if (!currentTemplate || currentTemplate.prompt !== val) {
                document.getElementById('single-prompt-template').value = 'custom';
            }
        }
        closeModal();
    }

    preview.addEventListener('click', openModal);
    btnEdit.addEventListener('click', openModal);
    btnClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);
    btnSave.addEventListener('click', saveValue);
}

function updateSinglePurpose(text) {
    const hiddenInput = document.getElementById('single-purpose');
    const preview = document.getElementById('single-purpose-preview');
    if (hiddenInput) hiddenInput.value = text;
    if (preview) {
        if (text.trim()) {
            preview.innerText = text.trim();
            preview.style.color = 'var(--text-primary)';
        } else {
            preview.innerText = '(No details entered)';
            preview.style.color = 'var(--text-secondary)';
        }
    }
}

function bindSingleEmailEvents() {
    document.getElementById('btn-generate-single').addEventListener('click', handleGenerate);
    document.getElementById('btn-refine').addEventListener('click', handleRefine);
    document.getElementById('btn-send-single').addEventListener('click', handleSendSingle);
    document.getElementById('btn-attach-file').addEventListener('click', handleAttach);
    document.getElementById('draft-output').addEventListener('input', () => { runEditorAnalysis(); pushEditorSnapshot(); });
    document.getElementById('btn-copy-draft').addEventListener('click', handleCopyDraft);
    document.getElementById('btn-save-template-single').addEventListener('click', handleSaveFromDraft);
    document.getElementById('btn-undo').addEventListener('click', handleUndo);
    document.getElementById('btn-redo').addEventListener('click', handleRedo);
    document.getElementById('btn-analyze-tone').addEventListener('click', handleAnalyzeTone);

    initPurposeModal();

    // AI Prompt templates change listener
    document.getElementById('single-prompt-template').addEventListener('change', (e) => {
        const val = e.target.value;
        if (val === 'custom') return;
        const templates = getSavedPromptTemplates();
        const found = templates.find(t => t.id === val);
        if (found) {
            updateSinglePurpose(found.prompt);
        }
    });
}

// ── Generate ──────────────────────────────────────────────────────────────
async function handleGenerate() {
    const btn = document.getElementById('btn-generate-single');
    setBtnLoading(btn, true, "✦ Generating...");
    const payload = {
        receiver:    getVal('receiver-name'),
        company:     getVal('receiver-company'),
        purpose:     getVal('single-purpose'),
        ai_provider: getActiveProvider(),
        model:       getActiveModel(),
    };
    const result = await pywebview.api.generate_email(payload);
    setBtnLoading(btn, false);
    if (result.success) {
        document.getElementById('draft-output').value = result.email;
        if (result.subject) document.getElementById('email-subject').value = result.subject;
        pushEditorSnapshot();
        runEditorAnalysis();
        // Reset tone analysis
        document.getElementById('tone-results').style.display = 'none';
        document.getElementById('tone-placeholder').style.display = 'block';
    } else {
        alert("Generation failed: " + result.error);
    }
}

// ── Refine ────────────────────────────────────────────────────────────────
async function handleRefine() {
    const instruction = getVal('refine-instruction');
    if (!instruction) { alert("Enter a refine instruction first."); return; }
    const btn = document.getElementById('btn-refine');
    setBtnLoading(btn, true, "Refining...");
    const result = await pywebview.api.refine_email({
        current_email: getVal('draft-output'),
        instruction,
        ai_provider: getActiveProvider(),
        model:       getActiveModel(),
    });
    setBtnLoading(btn, false);
    if (result.success) {
        document.getElementById('draft-output').value = result.email;
        pushEditorSnapshot();
        runEditorAnalysis();
    } else {
        alert("Refine failed: " + result.error);
    }
}

// ── Send ──────────────────────────────────────────────────────────────────
async function handleSendSingle() {
    const btn     = document.getElementById('btn-send-single');
    const flash   = document.getElementById('flash-single');
    const subject = getVal('email-subject') || ("Re: " + getVal('single-purpose'));
    const body    = getVal('draft-output');
    const to      = getVal('receiver-email');

    if (!body)  { alert("Draft is empty."); return; }
    if (!to)    { alert("Recipient email is required."); return; }

    // Show SMTP console
    const consoleEl = document.getElementById('smtp-console-single');
    if (consoleEl) consoleEl.style.display = 'block';

    setBtnLoading(btn, true, "⏳ Sending...");
    const result = await pywebview.api.send_email({
        smtp_provider: getVal('smtp-provider-settings'),
        smtp_email:    getVal('smtp-email-settings'),
        smtp_password: getVal('smtp-password-settings'),
        to_email:  to,
        subject,
        body,
        attachments: collectAttachments(),
        log_id: 'single',
    });
    setBtnLoading(btn, false);
    showFlash('flash-single', result.success ? "✔ Sent!" : "✘ " + result.error);
    if (result.success && typeof loadHistory === 'function') loadHistory();
}

// ── Attachments ───────────────────────────────────────────────────────────
async function handleAttach() {
    const result = await pywebview.api.pick_files({ multiple: true });
    if (result && result.length) {
        const list = document.getElementById('attachment-list');
        result.forEach(path => {
            const name = path.split(/[/\\]/).pop();
            const item = document.createElement('div');
            item.className    = 'attachment-item';
            item.dataset.path = path;
            item.innerHTML    = `<span title="${path}">${name}</span>
                <button class="remove-attach" onclick="this.closest('.attachment-item').remove()">✕</button>`;
            list.appendChild(item);
        });
    }
}

function collectAttachments() {
    return Array.from(document.querySelectorAll('.attachment-item')).map(el => el.dataset.path);
}

// ── Copy Draft ────────────────────────────────────────────────────────────
function handleCopyDraft() {
    const text = getVal('draft-output');
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        showFlash('flash-copy', '📋 Copied!');
    });
}

// ── Save As Template ──────────────────────────────────────────────────────
async function handleSaveFromDraft() {
    const name = prompt("Template name:");
    if (!name) return;
    const body = getVal('draft-output');
    await pywebview.api.save_template({ name, body, category: "Draft" });
    await renderTemplates();
    showFlash('flash-single', '✔ Saved as template');
}

// ── Spam & Readability Analyser ───────────────────────────────────────────
const SPAM_KEYWORDS = [
    "free", "urgent", "act now", "limited time", "click here", "100%",
    "buy now", "winner", "prize", "congratulations", "cash", "no cost",
    "guarantee", "risk-free"
];

function runEditorAnalysis() {
    const text        = (getVal('draft-output') || '').toLowerCase();
    const wordCount   = text.trim().split(/\s+/).filter(Boolean).length;
    const charCount   = text.length;
    const sentences   = text.split(/[.!?]+/).filter(s => s.trim()).length || 1;
    const avgWords    = (wordCount / sentences).toFixed(1);
    const matches     = SPAM_KEYWORDS.filter(k => text.includes(k));
    const spamScore   = Math.min(10, Math.round((matches.length / SPAM_KEYWORDS.length) * 100));
    const readability = wordCount < 50 ? "Short" : avgWords < 15 ? "Good" : avgWords < 20 ? "Fair" : "Dense";

    document.getElementById('stat-words').innerText   = wordCount;
    document.getElementById('stat-chars').innerText   = charCount;
    document.getElementById('stat-readability').innerText = readability;
    document.getElementById('stat-spam').innerText    = spamScore + "%";
    document.getElementById('stat-spam').style.color  =
        spamScore > 30 ? 'var(--danger-color)' : spamScore > 15 ? 'var(--warning-color)' : 'var(--success-color)';
    document.getElementById('stat-keywords').innerText = matches.length > 0 ? matches.join(', ') : '(none)';
}

// ── Tone Analysis ─────────────────────────────────────────────────────────
async function handleAnalyzeTone() {
    const body = getVal('draft-output');
    if (!body.trim()) { alert('Generate an email first.'); return; }
    const btn = document.getElementById('btn-analyze-tone');
    setBtnLoading(btn, true, '✦ Analyzing...');
    const result = await pywebview.api.analyze_email_tone({
        body,
        ai_provider: getActiveProvider(),
        model:       getActiveModel(),
    });
    setBtnLoading(btn, false);
    if (!result.success) { alert('Tone analysis failed: ' + result.error); return; }
    const d = result.data;
    // Show results
    document.getElementById('tone-results').style.display      = 'block';
    document.getElementById('tone-placeholder').style.display  = 'none';
    // Formality
    document.getElementById('tone-formality-val').innerText  = d.formality + '/100';
    document.getElementById('tone-formality-bar').style.width = d.formality + '%';
    // Friendliness
    document.getElementById('tone-friendly-val').innerText  = d.friendliness + '/100';
    document.getElementById('tone-friendly-bar').style.width = d.friendliness + '%';
    // Urgency
    document.getElementById('tone-urgency-val').innerText  = d.urgency + '/100';
    document.getElementById('tone-urgency-bar').style.width = d.urgency + '%';
    // Clarity
    document.getElementById('tone-clarity-val').innerText  = d.clarity + '/100';
    document.getElementById('tone-clarity-bar').style.width = d.clarity + '%';
    // Advice
    const adviceEl = document.getElementById('tone-advice');
    if (adviceEl) adviceEl.innerText = d.advice ? '💡 ' + d.advice : '';
}

// ── SMTP Log (global, called by Python via evaluate_js) ───────────────────
function appendSmtpLog(targetId, msg) {
    const boxId = targetId === 'bulk' ? 'smtp-log-bulk' : 'smtp-log-single';
    const box = document.getElementById(boxId);
    if (!box) return;
    const line = document.createElement('div');
    line.innerText = msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}
