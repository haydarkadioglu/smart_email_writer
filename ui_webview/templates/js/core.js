/* ==========================================================================
   core.js  –  App bootstrap, global state, tabs, theme, model dropdowns
   ========================================================================== */

// ── Provider registry ─────────────────────────────────────────────────────
const PROVIDERS = [
    { id: "gemini",     label: "Gemini",     modelsKey: "gemini_models",     envKey: "GEMINI_API_KEY"     },
    { id: "groq",       label: "Groq",       modelsKey: "groq_models",       envKey: "GROQ_API_KEY"       },
    { id: "openai",     label: "OpenAI",     modelsKey: "openai_models",     envKey: "OPENAI_API_KEY"     },
    { id: "claude",     label: "Claude",     modelsKey: "claude_models",     envKey: "CLAUDE_API_KEY"     },
    { id: "deepseek",   label: "DeepSeek",   modelsKey: "deepseek_models",   envKey: "DEEPSEEK_API_KEY"   },
    { id: "openrouter", label: "OpenRouter", modelsKey: "openrouter_models", envKey: "OPENROUTER_API_KEY" },
];

// ── Global State ──────────────────────────────────────────────────────────
let appConfig = null;

// ── Init ──────────────────────────────────────────────────────────────────
window.addEventListener('pywebviewready', async () => {
    try {
        updateApiStatus("Initializing...", "connecting");
        appConfig = await pywebview.api.get_config();

        // Build all provider <option> lists dynamically
        buildProviderDropdowns();

        // Apply persisted theme
        setTheme(appConfig.settings.theme || "obsidian-dark");

        // Seed forms
        populateConfigDefaults();
        populateProfileForm();
        updateModelDropdowns('settings-default-provider', 'settings-default-model');

        // Bind all modules
        bindNavEvents();
        bindSingleEmailEvents();
        bindBulkEmailEvents();
        bindTemplateEvents();
        bindProfileAndSettingsEvents();

        // Boot-time data loads
        if (typeof updateSinglePromptTemplateDropdown === 'function') {
            updateSinglePromptTemplateDropdown();
        }
        await renderTemplates();
        await loadHistory();
        runEditorAnalysis();
        renderApiKeyStatus();

        updateApiStatus("Connected", "connected");
    } catch (err) {
        updateApiStatus("Init error", "disconnected");
        console.error("Init error:", err);
    }
});

// ── Provider dropdowns ────────────────────────────────────────────────────
function buildProviderDropdowns() {
    const targets = ['settings-default-provider'];
    targets.forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = PROVIDERS.map(p =>
            `<option value="${p.id}">${p.label}</option>`
        ).join('');
    });
}

function updateModelDropdowns(providerId, modelId) {
    const provider = getVal(providerId);
    const meta     = PROVIDERS.find(p => p.id === provider);
    if (!meta || !appConfig) return;
    const models = appConfig[meta.modelsKey] || [];
    const saved  = appConfig.settings?.[provider + "_model"];
    populateSelect(modelId, models, saved || models[0]);
}

// ── API Key status badges ─────────────────────────────────────────────────
function renderApiKeyStatus() {
    const grid = document.getElementById('api-key-status-grid');
    if (!grid || !appConfig?.api_keys_configured) return;
    grid.innerHTML = PROVIDERS.map(p => {
        const ok = appConfig.api_keys_configured[p.id];
        return `
        <div class="api-key-badge ${ok ? 'configured' : 'missing'}">
            <span class="api-key-badge-dot"></span>
            <span>${p.label}</span>
            <span class="api-key-badge-status">${ok ? 'Configured' : 'Missing'}</span>
        </div>`;
    }).join('');
}

// ── Status Dot ────────────────────────────────────────────────────────────
function updateApiStatus(text, state) {
    const el  = document.querySelector('.status-indicator');
    const lbl = document.getElementById('api-status');
    if (!el || !lbl) return;
    lbl.innerText = text;
    el.className  = "status-indicator" + (state === "connected" ? " connected" : "");
}

// ── Tab Navigation ────────────────────────────────────────────────────────
function bindNavEvents() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
    });
}

function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
    });
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    const section = document.getElementById(tabId);
    if (section) section.classList.add('active');

    if (tabId === 'history')   loadHistory();
    if (tabId === 'templates') renderTemplates();
}

// ── Themes ────────────────────────────────────────────────────────────────
function setTheme(name) {
    document.documentElement.setAttribute('data-theme', name);
    document.querySelectorAll('.theme-card').forEach(c => {
        c.classList.toggle('active', c.getAttribute('data-theme-val') === name);
    });
}

// ── Config Defaults ───────────────────────────────────────────────────────
function populateConfigDefaults() {
    const s = appConfig.settings || {};
    const smtpProv = s.smtp_provider  || appConfig.env_smtp_provider || "Gmail";
    const smtpEmail = s.smtp_email     || appConfig.env_smtp_email    || "";
    const smtpPass = s.smtp_password  || "";
    setVal('smtp-provider-settings', smtpProv);
    setVal('smtp-email-settings',    smtpEmail);
    setVal('smtp-password-settings', smtpPass);

    if (typeof updateSinglePurpose === 'function') {
        updateSinglePurpose(s.default_purpose || "");
    } else {
        setVal('single-purpose', s.default_purpose || "");
    }

    // Restore saved API keys
    setVal('settings-api-key-gemini',     s.api_key_gemini || "");
    setVal('settings-api-key-groq',       s.api_key_groq || "");
    setVal('settings-api-key-openai',     s.api_key_openai || "");
    setVal('settings-api-key-claude',     s.api_key_claude || "");
    setVal('settings-api-key-deepseek',   s.api_key_deepseek || "");
    setVal('settings-api-key-openrouter', s.api_key_openrouter || "");

    // Restore saved provider selections
    setVal('settings-default-provider', s.ai_provider || "gemini");
    setVal('settings-model-override', s.model_override || "");
    setVal('settings-purpose', s.default_purpose || "");
    
    // Trigger populating default model selector
    updateModelDropdowns('settings-default-provider', 'settings-default-model');
}

// ── Helpers ───────────────────────────────────────────────────────────────
function getVal(id)     { return document.getElementById(id)?.value ?? ""; }
function setVal(id, v)  { const el = document.getElementById(id); if (el) el.value = v; }
function getChecked(id) { return document.getElementById(id)?.checked ?? false; }

function populateSelect(id, options, selectedValue) {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = "";
    (options || []).forEach(opt => {
        const o = document.createElement('option');
        o.value = opt; o.innerText = opt;
        if (opt === selectedValue) o.selected = true;
        sel.appendChild(o);
    });
}

function setBtnLoading(btn, loading, loadingText) {
    if (loading) {
        btn.disabled = true;
        btn.dataset.origHtml = btn.innerHTML;
        btn.innerText = loadingText;
    } else {
        btn.disabled = false;
        btn.innerHTML = btn.dataset.origHtml || btn.innerText;
    }
}

function showFlash(elId, text, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.innerText = text;
    el.style.display = "inline-block";
    el.style.background = isError ? 'var(--danger-color)' : 'var(--success-color)';
    setTimeout(() => el.style.display = "none", 3500);
}

function getActiveProvider() {
    return getVal('settings-default-provider') || 'gemini';
}

function getActiveModel() {
    return getVal('settings-model-override') || getVal('settings-default-model') || '';
}
