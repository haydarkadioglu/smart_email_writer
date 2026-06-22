/* ==========================================================================
   settings.js  –  Settings tab: save settings, SMTP test, usage modal
   ========================================================================== */

// ── Save settings ─────────────────────────────────────────────────────────
async function saveSettings() {
    const btn = document.getElementById('btn-save-settings');
    setBtnLoading(btn, true, "Saving...");

    const provider     = getVal('settings-default-provider');
    const model        = getVal('settings-default-model');
    const modelOverride = getVal('settings-model-override');

    // Sync any in-progress API key input to localApiKeys before saving
    const apiKeyInput = document.getElementById('settings-api-key-input');
    const providerSel = document.getElementById('settings-default-provider');
    if (apiKeyInput && providerSel) {
        window.localApiKeys = window.localApiKeys || {};
        window.localApiKeys[providerSel.value] = apiKeyInput.value;
    }

    const payload = {
        smtp_provider:      getVal('smtp-provider-settings'),
        smtp_email:         getVal('smtp-email-settings'),
        smtp_password:      getVal('smtp-password-settings'),
        ai_provider:        provider,
        default_purpose:    getVal('settings-purpose'),
        model_override:     modelOverride,
        theme:              document.documentElement.getAttribute('data-theme'),
        api_key_gemini:     window.localApiKeys?.gemini     || "",
        api_key_groq:       window.localApiKeys?.groq       || "",
        api_key_openai:     window.localApiKeys?.openai     || "",
        api_key_claude:     window.localApiKeys?.claude     || "",
        api_key_deepseek:   window.localApiKeys?.deepseek   || "",
        api_key_openrouter: window.localApiKeys?.openrouter || "",
    };
    payload[provider + "_model"] = model;

    const result = await pywebview.api.save_settings(payload);
    setBtnLoading(btn, false);
    showFlash('flash-settings', result.success ? '✔ Settings saved' : '✘ ' + result.error, !result.success);

    if (result.success) {
        if (appConfig) {
            appConfig.settings = { ...appConfig.settings, ...result.settings };
            try {
                const latestConfig = await pywebview.api.get_config();
                appConfig.api_keys_configured = latestConfig.api_keys_configured;
                renderApiKeyStatus();
            } catch (err) {
                console.error("Failed to refresh API status badges:", err);
            }
        }
    }
}

// ── SMTP test ─────────────────────────────────────────────────────────────
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

// ── Usage stats modal ─────────────────────────────────────────────────────
async function openUsageModal() {
    const modal = document.getElementById('usage-modal');
    if (modal) modal.classList.add('active');
    const result = await pywebview.api.get_usage_stats();
    if (!result.success) return;
    document.getElementById('usage-total-tokens').innerText = result.total_tokens.toLocaleString();
    document.getElementById('usage-total-cost').innerText   = '$' + result.total_cost.toFixed(6);
    document.getElementById('usage-entry-count').innerText  = result.logs.length;
    const tbody = document.getElementById('usage-table-body');
    if (!tbody) return;
    if (!result.logs.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary)">No usage data yet.</td></tr>';
        return;
    }
    tbody.innerHTML = result.logs.map(e => `
        <tr>
            <td>${e.ts}</td>
            <td>${e.provider}</td>
            <td style="font-size:12px;color:var(--text-secondary)">${e.model || '—'}</td>
            <td>${e.tokens_in}</td>
            <td>${e.tokens_out}</td>
            <td style="color:var(--success-color)">$${e.cost_usd.toFixed(6)}</td>
        </tr>
    `).join('');
}

function closeUsageModal() {
    document.getElementById('usage-modal')?.classList.remove('active');
}

async function clearUsageLogs() {
    if (!confirm('Clear all usage history? This cannot be undone.')) return;
    await pywebview.api.clear_usage_logs();
    await openUsageModal();
}

// ── Bind settings & profile events ────────────────────────────────────────
function bindProfileAndSettingsEvents() {
    document.getElementById('btn-save-profile')?.addEventListener('click',  saveProfile);
    document.getElementById('btn-clear-history')?.addEventListener('click', clearHistory);
    document.getElementById('btn-save-settings')?.addEventListener('click', saveSettings);
    document.getElementById('btn-test-smtp')?.addEventListener('click',     testSmtpConnection);

    // Usage stats modal
    document.getElementById('btn-open-usage')?.addEventListener('click', openUsageModal);
    ['btn-close-usage-modal', 'btn-close-usage-modal2'].forEach(id =>
        document.getElementById(id)?.addEventListener('click', closeUsageModal)
    );
    document.getElementById('btn-clear-usage')?.addEventListener('click', clearUsageLogs);
    document.getElementById('usage-modal')?.addEventListener('click', e => {
        if (e.target === document.getElementById('usage-modal')) closeUsageModal();
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
    document.querySelector('[data-tab="profile"]')?.addEventListener('click', populateProfileForm);
}
