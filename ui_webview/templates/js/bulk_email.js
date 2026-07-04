/* ==========================================================================
   bulk_email.js  –  Bulk Email tab logic
   ========================================================================== */

let uploadedBulkData   = [];   // rows parsed from CSV/Excel
let approvalQueue      = [];   // [{recipient, subject, body}]
let currentApprovalIdx = 0;
let bulkAttachments    = [];   // file paths to attach to every bulk email

function bindBulkEmailEvents() {
    // Upload area
    document.getElementById('bulk-upload-area').addEventListener('click',  handleBulkUpload);
    document.getElementById('bulk-upload-area').addEventListener('dragover', e => e.preventDefault());
    document.getElementById('bulk-upload-area').addEventListener('drop',    handleBulkDrop);



    // Mode toggles
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('single-purpose-section').style.display =
                btn.dataset.mode === 'single' ? 'block' : 'none';
            document.getElementById('per-recipient-section').style.display =
                btn.dataset.mode === 'per' ? 'block' : 'none';
        });
    });

    document.getElementById('btn-bulk-preview').addEventListener('click', handleBulkPreview);
    document.getElementById('btn-bulk-generate').addEventListener('click', handleBulkGenerate);
    document.getElementById('btn-bulk-send-all').addEventListener('click', handleBulkSendAll);
    document.getElementById('btn-bulk-attach')?.addEventListener('click',  handleBulkAttach);

    // Approval workflow navigation
    document.getElementById('btn-approve-send').addEventListener('click',  handleApproveSend);
    document.getElementById('btn-approve-skip').addEventListener('click',  handleApproveSkip);
    document.getElementById('btn-approve-edit').addEventListener('click',  handleApproveEdit);

    // Column mapping confirm button
    const confirmBtn = document.getElementById('btn-confirm-mapping');
    if (confirmBtn) confirmBtn.addEventListener('click', confirmColumnMapping);
}

// ── Upload / Drop ─────────────────────────────────────────────────────────
async function handleBulkUpload() {
    const result = await pywebview.api.pick_files({ multiple: false, file_types: ['.csv', '.xlsx'] });
    if (result && result.length) processUploadedFile(result[0]);
}

function handleBulkDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer?.files?.[0];
    if (file) processUploadedFile(file.path || file.name);
}

async function processUploadedFile(path) {
    const result = await pywebview.api.parse_bulk_file({ path });
    if (!result.success) { alert("Could not parse file: " + result.error); return; }

    uploadedBulkData = result.rows;
    document.getElementById('upload-status').innerHTML =
        `<span class="file-badge">📎 ${uploadedBulkData.length} recipients loaded</span>`;

    renderBulkPreview(result.rows.slice(0, 5));
    renderCustomFieldInputs(result.columns || []);

    // Show and populate column mapping panel
    const cols = result.columns || [];
    if (cols.length > 0) {
        populateMappingDropdowns(cols);
        document.getElementById('bulk-mapping-section').style.display = 'block';
    }
}

function renderBulkPreview(rows) {
    const container = document.getElementById('bulk-data-preview');
    if (!rows.length) { container.innerHTML = '<p>No preview available.</p>'; return; }

    const cols     = Object.keys(rows[0]);
    const thHTML   = cols.map(c => `<th>${c}</th>`).join('');
    const rowsHTML = rows.map(r => `<tr>${cols.map(c => `<td>${r[c] || ''}</td>`).join('')}</tr>`).join('');
    container.innerHTML = `
        <table class="data-table">
            <thead><tr>${thHTML}</tr></thead>
            <tbody>${rowsHTML}</tbody>
        </table>`;
}

function renderCustomFieldInputs(columns) {
    const container = document.getElementById('custom-fields-container');
    if (!container) return;
    container.innerHTML = '';
    columns.forEach(col => {
        container.innerHTML += `
            <div class="form-group">
                <label>{{${col}}} default value</label>
                <input id="cf-${col}" type="text" class="form-input" placeholder="leave empty to use data" />
            </div>`;
    });
}

// ── Preview Emails ────────────────────────────────────────────────────────
async function handleBulkPreview() {
    const purpose = getVal('bulk-common-purpose');
    if (!purpose && uploadedBulkData.length) {
        alert("Enter a common email purpose first."); return;
    }
    const result = await pywebview.api.preview_bulk({
        rows:    uploadedBulkData,
        purpose,
        subject: getVal('bulk-subject-template'),
    });
    if (!result.success) { alert(result.error); return; }
    renderBulkPreview(result.previews);
}

// ── Generate All ──────────────────────────────────────────────────────────
async function handleBulkGenerate() {
    if (!uploadedBulkData.length) { alert("Upload a recipient file first."); return; }
    const btn = document.getElementById('btn-bulk-generate');
    setBtnLoading(btn, true, "⏳ Generating...");

    const payload = {
        rows:        uploadedBulkData,
        purpose:     getVal('bulk-common-purpose'),
        ai_provider: getActiveProvider(),
        model:       getActiveModel(),
        subject:     getVal('bulk-subject-template'),
    };
    const result = await pywebview.api.generate_bulk(payload);
    setBtnLoading(btn, false);

    if (!result.success) { alert(result.error); return; }

    approvalQueue      = result.emails;
    currentApprovalIdx = 0;
    document.getElementById('approval-section').style.display = 'block';
    showApprovalEmail(currentApprovalIdx);
    updateBulkProgress(0, approvalQueue.length);
}

// ── Column Mapping ────────────────────────────────────────────────────────
function populateMappingDropdowns(cols) {
    const GUESS = {
        'map-name':    ['name', 'ad', 'isim', 'full name', 'fullname', 'contact'],
        'map-email':   ['email', 'e-mail', 'mail', 'eposta', 'e-posta'],
        'map-company': ['company', 'firma', 'şirket', 'sirket', 'organization', 'org'],
        'map-purpose': ['purpose', 'amaç', 'amac', 'description', 'message', 'topic'],
    };
    ['map-name', 'map-email', 'map-company', 'map-purpose'].forEach(selId => {
        const sel = document.getElementById(selId);
        if (!sel) return;
        // Build options
        const baseOpt = selId === 'map-name' || selId === 'map-email'
            ? `<option value="">— select —</option>` : `<option value="">(none)</option>`;
        sel.innerHTML = baseOpt + cols.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
        // Auto-guess
        const guesses = GUESS[selId] || [];
        const matched = cols.find(c => guesses.some(g => c.toLowerCase().includes(g)));
        if (matched) sel.value = matched;
    });
}

function confirmColumnMapping() {
    const nameCol    = document.getElementById('map-name')?.value;
    const emailCol   = document.getElementById('map-email')?.value;
    const companyCol = document.getElementById('map-company')?.value;
    const purposeCol = document.getElementById('map-purpose')?.value;

    if (!nameCol || !emailCol) {
        showFlash('flash-mapping', '⚠ Name and Email columns are required');
        return;
    }

    // Normalise each row to have standard keys, then skip rows with no email
    const totalBefore = uploadedBulkData.length;
    uploadedBulkData = uploadedBulkData
        .map(row => {
            const normalised = Object.assign({}, row);
            normalised.Name    = row[nameCol]    || '';
            normalised.Email   = (row[emailCol]  || '').trim();
            if (companyCol) normalised.Company = row[companyCol] || '';
            if (purposeCol) normalised.purpose  = row[purposeCol] || '';
            return normalised;
        })
        .filter(row => row.Email.length > 0);   // ← skip empty emails

    const skipped = totalBefore - uploadedBulkData.length;
    const skipMsg = skipped > 0 ? ` (${skipped} row${skipped > 1 ? 's' : ''} skipped — no email)` : '';
    showFlash('flash-mapping', `✔ Mapped ${uploadedBulkData.length} recipients${skipMsg}`);
    document.getElementById('bulk-mapping-section').style.display = 'none';
}

// ── Send All ──────────────────────────────────────────────────────────────
async function handleBulkSendAll() {
    if (!uploadedBulkData || !uploadedBulkData.length) {
        alert("Please upload and map a CSV or Excel file first.");
        return;
    }

    const btn = document.getElementById('btn-bulk-send-all');
    
    // 1. If emails have not been generated yet, generate them first!
    if (!approvalQueue.length) {
        const genBtn = document.getElementById('btn-bulk-generate');
        setBtnLoading(btn, true, "⏳ Generating...");
        if (genBtn) setBtnLoading(genBtn, true, "⏳ Generating...");

        const payload = {
            rows:        uploadedBulkData,
            purpose:     getVal('bulk-common-purpose'),
            ai_provider: getActiveProvider(),
            model:       getActiveModel(),
            subject:     getVal('bulk-subject-template'),
        };
        const result = await pywebview.api.generate_bulk(payload);
        if (genBtn) setBtnLoading(genBtn, false);

        if (!result.success) {
            setBtnLoading(btn, false);
            alert("Generation failed: " + result.error);
            return;
        }

        approvalQueue      = result.emails;
        currentApprovalIdx = 0;
        document.getElementById('approval-section').style.display = 'block';
        showApprovalEmail(currentApprovalIdx);
        updateBulkProgress(0, approvalQueue.length);
    }

    // 2. Send all emails
    setBtnLoading(btn, true, "⏳ Sending...");

    // Show SMTP console
    const consoleEl = document.getElementById('smtp-console-bulk');
    if (consoleEl) consoleEl.style.display = 'block';

    const delay = parseInt(getVal('email-delay-seconds') || "2");
    const result = await pywebview.api.send_bulk({
        emails:        approvalQueue,
        smtp_provider: getVal('smtp-provider-settings'),
        smtp_email:    getVal('smtp-email-settings'),
        smtp_password: getVal('smtp-password-settings'),
        delay_seconds: delay,
        attachments:   bulkAttachments,
        log_id:        'bulk',
    });
    setBtnLoading(btn, false);
    if (result.success) {
        showFlash('flash-bulk', `✔ Sent ${result.sent}/${result.total}`);
    } else {
        alert("Bulk send error: " + result.error);
    }
}

// ── Approval Workflow ─────────────────────────────────────────────────────
function showApprovalEmail(idx) {
    const email = approvalQueue[idx];
    if (!email) return;
    document.getElementById('approval-counter').innerText =
        `${idx + 1} / ${approvalQueue.length}`;
    document.getElementById('approval-to').innerText      = email.to || "—";
    document.getElementById('approval-subject').innerText = email.subject || "—";
    document.getElementById('approval-body-editor').value = email.body;
}

function updateBulkProgress(done, total) {
    const pct = total ? Math.round((done / total) * 100) : 0;
    const bar  = document.getElementById('bulk-progress-bar');
    const txt  = document.getElementById('bulk-progress-text');
    if (bar) bar.style.width = pct + '%';
    if (txt) txt.innerText  = `${done}/${total} (${pct}%)`;
}

function handleApproveSend() {
    // Save any edits back into the queue
    approvalQueue[currentApprovalIdx].body = getVal('approval-body-editor');
    currentApprovalIdx++;
    if (currentApprovalIdx >= approvalQueue.length) {
        document.getElementById('approval-section').style.display = 'none';
        alert("All emails approved. Click 'Send All' to dispatch.");
        return;
    }
    showApprovalEmail(currentApprovalIdx);
    updateBulkProgress(currentApprovalIdx, approvalQueue.length);
}

function handleApproveSkip() {
    approvalQueue.splice(currentApprovalIdx, 1);
    if (currentApprovalIdx >= approvalQueue.length) currentApprovalIdx = approvalQueue.length - 1;
    if (approvalQueue.length === 0) {
        document.getElementById('approval-section').style.display = 'none'; return;
    }
    showApprovalEmail(currentApprovalIdx);
    updateBulkProgress(currentApprovalIdx, approvalQueue.length);
}

function handleApproveEdit() {
    // Body is already editable; just keep current index
    const textarea = document.getElementById('approval-body-editor');
    textarea.focus();
    textarea.setSelectionRange(0, 0);
}

// ── Bulk Attachments ──────────────────────────────────────────────────────
async function handleBulkAttach() {
    const result = await pywebview.api.pick_files({ multiple: true });
    if (!result || !result.length) return;

    const list = document.getElementById('bulk-attachment-list');
    result.forEach(path => {
        if (bulkAttachments.includes(path)) return;   // no duplicates
        bulkAttachments.push(path);

        const name = path.split(/[/\\]/).pop();
        const tag  = document.createElement('div');
        tag.className = 'attachment-item';
        tag.dataset.path = path;
        tag.innerHTML = `<span title="${path}">${name}</span>
            <button class="remove-attach" onclick="removeBulkAttachment(this, '${path.replace(/'/g, "\\'")}')">✕</button>`;
        list.appendChild(tag);
    });
}

function removeBulkAttachment(btn, path) {
    bulkAttachments = bulkAttachments.filter(p => p !== path);
    btn.closest('.attachment-item').remove();
}
