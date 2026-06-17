/* ==========================================================================
   single_email.js  –  Single Email tab logic
   ========================================================================== */

function bindSingleEmailEvents() {
    document.getElementById('btn-generate-single').addEventListener('click', handleGenerate);
    document.getElementById('btn-refine').addEventListener('click', handleRefine);
    document.getElementById('btn-send-single').addEventListener('click', handleSendSingle);
    document.getElementById('btn-attach-file').addEventListener('click', handleAttach);
    document.getElementById('draft-output').addEventListener('input', runEditorAnalysis);
    document.getElementById('btn-copy-draft').addEventListener('click', handleCopyDraft);
    document.getElementById('btn-save-template-single').addEventListener('click', handleSaveFromDraft);
}

// ── Generate ──────────────────────────────────────────────────────────────
async function handleGenerate() {
    const btn = document.getElementById('btn-generate-single');
    setBtnLoading(btn, true, "✦ Generating...");
    const payload = {
        name:        getVal('sender-name'),
        email:       getVal('sender-email'),
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
        runEditorAnalysis();
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

    setBtnLoading(btn, true, "⏳ Sending...");
    const result = await pywebview.api.send_email({
        smtp_provider: getVal('smtp-provider'),
        smtp_email:    getVal('smtp-email'),
        smtp_password: getVal('smtp-password'),
        to_email:  to,
        subject,
        body,
        attachments: collectAttachments(),
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
