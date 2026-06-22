/* ==========================================================================
   history_ui.js  –  History tab: load, render, clear
   ========================================================================== */

async function loadHistory() {
    const result = await pywebview.api.get_history({ limit: 50 });
    const list   = document.getElementById('history-list');
    if (!list) return;

    if (!result.success || !result.history.length) {
        list.innerHTML = '<p style="color:var(--text-secondary)">No history yet.</p>';
        return;
    }
    list.innerHTML = result.history.map(item => historyRow(item)).join('');

    list.querySelectorAll('[data-history-reuse]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('draft-output').value = btn.dataset.historyReuse;
            switchTab('single-email');
            runEditorAnalysis();
        });
    });
}

function historyRow(item) {
    const date    = new Date(item.timestamp).toLocaleString();
    const preview = (item.body || '').slice(0, 200).replace(/\n/g, ' ');
    const status  = item.sent
        ? '<span class="badge badge-success">Sent</span>'
        : '<span class="badge badge-secondary">Draft</span>';
    return `
    <div class="history-item">
        <div class="history-item-header">
            <div class="history-item-meta">
                ${status}
                <span>To: ${escapeHtml(item.to || '—')}</span>
                <span>${date}</span>
            </div>
            <button class="btn btn-sm btn-secondary" data-history-reuse="${escapeHtml(item.body || '')}">
                Reuse Draft
            </button>
        </div>
        <div class="history-item-body">${escapeHtml(preview)}${item.body.length > 200 ? '…' : ''}</div>
    </div>`;
}

async function clearHistory() {
    if (!confirm("Clear all history?")) return;
    await pywebview.api.clear_history();
    loadHistory();
}
