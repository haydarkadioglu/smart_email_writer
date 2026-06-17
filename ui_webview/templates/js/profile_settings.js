/* ==========================================================================
   profile_settings.js  –  Profile, History and Settings tab logic
   ========================================================================== */

// ═══════════════════════════════════════════════════════════════════════════
//  PROFILE
// ═══════════════════════════════════════════════════════════════════════════

function populateProfileForm() {
    const p = appConfig.settings.profile || {};
    setVal('profile-name',      p.name       || '');
    setVal('profile-email',     p.email      || '');
    setVal('profile-company',   p.company    || '');
    setVal('profile-role',      p.role       || '');
    setVal('profile-website',   p.website    || '');
    setVal('profile-signature', p.signature  || '');
}

async function saveProfile() {
    const btn = document.getElementById('btn-save-profile');
    setBtnLoading(btn, true, "Saving...");
    const result = await pywebview.api.save_config({
        profile: {
            name:      getVal('profile-name'),
            email:     getVal('profile-email'),
            company:   getVal('profile-company'),
            role:      getVal('profile-role'),
            website:   getVal('profile-website'),
            signature: getVal('profile-signature'),
        }
    });
    setBtnLoading(btn, false);
    showFlash('flash-profile', result.success ? '✔ Profile saved' : '✘ ' + result.error);


}

// ═══════════════════════════════════════════════════════════════════════════
//  HISTORY
// ═══════════════════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════════════════
//  SETTINGS
// ═══════════════════════════════════════════════════════════════════════════

async function saveSettings() {
    const btn = document.getElementById('btn-save-settings');
    setBtnLoading(btn, true, "Saving...");
    
    const provider = getVal('settings-default-provider');
    const model = getVal('settings-default-model');
    const modelOverride = getVal('settings-model-override');
    
    const payload = {
        smtp_provider:       getVal('smtp-provider-settings'),
        smtp_email:          getVal('smtp-email-settings'),
        smtp_password:       getVal('smtp-password-settings'),
        ai_provider:         provider,
        default_purpose:     getVal('settings-purpose'),
        model_override:      modelOverride,
        theme:               document.documentElement.getAttribute('data-theme'),
    };
    payload[provider + "_model"] = model;

    const result = await pywebview.api.save_settings(payload);
    setBtnLoading(btn, false);
    showFlash('flash-settings', result.success ? '✔ Settings saved' : '✘ ' + result.error, !result.success);
    if (result.success) {
        if (appConfig) appConfig.settings = { ...appConfig.settings, ...result.settings };
    }
}

async function testSmtpConnection() {
    const btn = document.getElementById('btn-test-smtp');
    setBtnLoading(btn, true, "Testing...");
    const result = await pywebview.api.test_smtp({
        smtp_provider: getVal('smtp-provider-settings'),
        smtp_email:    getVal('smtp-email-settings'),
        smtp_password: getVal('smtp-password-settings'),
    });
    setBtnLoading(btn, false);
    showFlash('flash-settings', result.success ? '✔ SMTP OK' : '✘ ' + result.error);
}

// ── Bind all profile & settings events ────────────────────────────────────
function bindProfileAndSettingsEvents() {
    document.getElementById('btn-save-profile').addEventListener('click',   saveProfile);
    document.getElementById('btn-clear-history').addEventListener('click',  clearHistory);
    document.getElementById('btn-save-settings').addEventListener('click',  saveSettings);
    document.getElementById('btn-test-smtp').addEventListener('click',      testSmtpConnection);

    // AI Provider change → refresh model list in Settings
    document.getElementById('settings-default-provider').addEventListener('change', () => {
        updateModelDropdowns('settings-default-provider', 'settings-default-model');
    });

    // Theme cards
    document.querySelectorAll('.theme-card').forEach(card => {
        card.addEventListener('click', async () => {
            const theme = card.getAttribute('data-theme-val');
            setTheme(theme);
            await pywebview.api.save_config({ theme });
            if (appConfig) appConfig.settings.theme = theme;
        });
    });

    // Sync sender fields to profile on profile tab open
    document.querySelector('[data-tab="profile"]').addEventListener('click', populateProfileForm);
}
