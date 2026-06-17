/* ==========================================================================
   templates.js  –  Template CRUD & rendering
   ========================================================================== */

let editingTemplateId = null;
let editingPromptTemplateId = null;

function bindTemplateEvents() {
    // Email templates
    document.getElementById('btn-new-template').addEventListener('click', openNewTemplateForm);
    document.getElementById('btn-save-template-form').addEventListener('click', saveTemplateForm);
    document.getElementById('btn-cancel-template-form').addEventListener('click', closeTemplateForm);

    // Prompt templates
    document.getElementById('btn-new-prompt-template').addEventListener('click', openNewPromptTemplateForm);
    document.getElementById('btn-save-prompt-template-form').addEventListener('click', savePromptTemplateForm);
    document.getElementById('btn-cancel-prompt-template-form').addEventListener('click', closePromptTemplateForm);

    // Toggle sub-tabs
    document.getElementById('btn-toggle-email-templates').addEventListener('click', () => switchTemplateSubTab('email'));
    document.getElementById('btn-toggle-prompt-templates').addEventListener('click', () => switchTemplateSubTab('prompt'));
}

// ── Render all templates ───────────────────────────────────────────────────
async function renderTemplates() {
    const result = await pywebview.api.list_templates();
    const grid   = document.getElementById('templates-grid');
    if (!grid) return;

    if (!result.success || !result.templates.length) {
        grid.innerHTML = '<p style="color:var(--text-secondary)">No saved templates yet.</p>';
        return;
    }

    grid.innerHTML = result.templates.map(t => templateCard(t)).join('');

    // Bind card buttons
    grid.querySelectorAll('[data-template-id]').forEach(btn => {
        const id = btn.dataset.templateId;
        if (btn.dataset.action === 'use')    btn.addEventListener('click', () => useTemplate(id));
        if (btn.dataset.action === 'edit')   btn.addEventListener('click', () => editTemplate(id, result.templates));
        if (btn.dataset.action === 'delete') btn.addEventListener('click', () => deleteTemplate(id));
    });
}

function templateCard(t) {
    const preview = (t.body || '').replace(/\n/g, ' ').slice(0, 130) + (t.body.length > 130 ? '…' : '');
    const cat     = t.category ? `<span class="badge">${t.category}</span>` : '';
    return `
    <div class="template-card">
        <div class="template-card-header">
            <h4>${escapeHtml(t.name)}</h4>
            <div style="display:flex;gap:6px;align-items:center;margin-top:4px;">
                ${cat}
                <span style="font-size:11px;color:var(--text-secondary);font-family:monospace">${t.id}</span>
            </div>
        </div>
        <p class="template-card-preview">${escapeHtml(preview)}</p>
        <div class="template-actions">
            <button class="btn btn-sm btn-primary" data-template-id="${t.id}" data-action="use">Use</button>
            <button class="btn btn-sm btn-secondary" data-template-id="${t.id}" data-action="edit">Edit</button>
            <button class="btn btn-sm btn-danger" data-template-id="${t.id}" data-action="delete">Delete</button>
        </div>
    </div>`;
}

// ── CRUD ──────────────────────────────────────────────────────────────────
function openNewTemplateForm() {
    editingTemplateId = null;
    document.getElementById('template-form-title').innerText = "New Template";
    setVal('template-form-name',     '');
    setVal('template-form-category', '');
    setVal('template-form-body',     '');
    document.getElementById('template-form-section').style.display = 'block';
}

function editTemplate(id, templates) {
    const t = templates.find(x => x.id === id);
    if (!t) return;
    editingTemplateId = id;
    document.getElementById('template-form-title').innerText = "Edit Template";
    setVal('template-form-name',     t.name);
    setVal('template-form-category', t.category || '');
    setVal('template-form-body',     t.body);
    document.getElementById('template-form-section').style.display = 'block';
}

async function saveTemplateForm() {
    const name = getVal('template-form-name');
    if (!name) { alert("Template name is required."); return; }
    const payload = {
        id:       editingTemplateId || undefined,
        name,
        category: getVal('template-form-category'),
        body:     getVal('template-form-body'),
    };
    const result = editingTemplateId
        ? await pywebview.api.update_template(payload)
        : await pywebview.api.save_template(payload);

    if (result.success) {
        closeTemplateForm();
        await renderTemplates();
    } else {
        alert("Save failed: " + result.error);
    }
}

async function deleteTemplate(id) {
    if (!confirm("Delete this template?")) return;
    await pywebview.api.delete_template({ id });
    await renderTemplates();
}

function closeTemplateForm() {
    document.getElementById('template-form-section').style.display = 'none';
}

// ── Use template in Single Email tab ─────────────────────────────────────
function useTemplate(id) {
    pywebview.api.get_template({ id }).then(result => {
        if (result.success) {
            document.getElementById('draft-output').value = result.template.body;
            switchTab('single-email');
            runEditorAnalysis();
        }
    });
}

// ── Util ──────────────────────────────────────────────────────────────────
function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── Sub-tab toggling ───────────────────────────────────────────────────────
function switchTemplateSubTab(type) {
    const btnEmail = document.getElementById('btn-toggle-email-templates');
    const btnPrompt = document.getElementById('btn-toggle-prompt-templates');
    const emailContainer = document.getElementById('email-templates-container');
    const promptContainer = document.getElementById('prompt-templates-container');
    const btnNewEmail = document.getElementById('btn-new-template');
    const btnNewPrompt = document.getElementById('btn-new-prompt-template');

    // Close forms
    closeTemplateForm();
    closePromptTemplateForm();

    if (type === 'email') {
        btnEmail.classList.add('active');
        btnPrompt.classList.remove('active');
        emailContainer.style.display = 'block';
        promptContainer.style.display = 'none';
        btnNewEmail.style.display = 'inline-block';
        btnNewPrompt.style.display = 'none';
    } else {
        btnEmail.classList.remove('active');
        btnPrompt.classList.add('active');
        emailContainer.style.display = 'none';
        promptContainer.style.display = 'block';
        btnNewEmail.style.display = 'none';
        btnNewPrompt.style.display = 'inline-block';
        
        renderPromptTemplates();
    }
}

// ── Render all prompt templates ─────────────────────────────────────────────
async function renderPromptTemplates() {
    const grid = document.getElementById('prompt-templates-grid');
    if (!grid) return;

    const list = getSavedPromptTemplates();
    if (!list.length) {
        grid.innerHTML = '<p style="color:var(--text-secondary)">No prompt templates yet.</p>';
        return;
    }

    grid.innerHTML = list.map(t => promptTemplateCard(t)).join('');

    // Bind card buttons
    grid.querySelectorAll('[data-prompt-id]').forEach(btn => {
        const id = btn.dataset.promptId;
        if (btn.dataset.action === 'edit')   btn.addEventListener('click', () => editPromptTemplate(id));
        if (btn.dataset.action === 'delete') btn.addEventListener('click', () => deletePromptTemplate(id));
    });
}

function promptTemplateCard(t) {
    const preview = (t.prompt || '').replace(/\n/g, ' ').slice(0, 130) + (t.prompt.length > 130 ? '…' : '');
    return `
    <div class="template-card">
        <div class="template-card-header">
            <h4>${escapeHtml(t.title)}</h4>
            <div style="display:flex;gap:6px;align-items:center;margin-top:4px;">
                <span style="font-size:11px;color:var(--text-secondary);font-family:monospace">${t.id}</span>
            </div>
        </div>
        <p class="template-card-preview">${escapeHtml(preview)}</p>
        <div class="template-actions">
            <button class="btn btn-sm btn-secondary" data-prompt-id="${t.id}" data-action="edit">Edit</button>
            <button class="btn btn-sm btn-danger" data-prompt-id="${t.id}" data-action="delete">Delete</button>
        </div>
    </div>`;
}

// ── CRUD for Prompt Templates ───────────────────────────────────────────────
function openNewPromptTemplateForm() {
    editingPromptTemplateId = null;
    document.getElementById('prompt-template-form-title').innerText = "New Prompt Template";
    setVal('prompt-template-form-name',   '');
    setVal('prompt-template-form-prompt', '');
    document.getElementById('prompt-template-form-section').style.display = 'block';
}

function closePromptTemplateForm() {
    document.getElementById('prompt-template-form-section').style.display = 'none';
}

function editPromptTemplate(id) {
    const list = getSavedPromptTemplates();
    const t = list.find(x => x.id === id);
    if (!t) return;
    editingPromptTemplateId = id;
    document.getElementById('prompt-template-form-title').innerText = "Edit Prompt Template";
    setVal('prompt-template-form-name',   t.title);
    setVal('prompt-template-form-prompt', t.prompt);
    document.getElementById('prompt-template-form-section').style.display = 'block';
}

async function savePromptTemplateForm() {
    const title = getVal('prompt-template-form-name');
    const promptText = getVal('prompt-template-form-prompt');
    if (!title) { alert("Prompt name is required."); return; }
    if (!promptText) { alert("Prompt details are required."); return; }

    const list = [...getSavedPromptTemplates()];

    if (editingPromptTemplateId) {
        // Update
        const idx = list.findIndex(x => x.id === editingPromptTemplateId);
        if (idx !== -1) {
            list[idx].title = title;
            list[idx].prompt = promptText;
        }
    } else {
        // Add
        const newId = 'prompt_' + Math.random().toString(36).substr(2, 9);
        list.push({
            id: newId,
            title,
            prompt: promptText
        });
    }

    // Save to settings config via python bridge save_config
    const result = await pywebview.api.save_config({
        prompt_templates: list
    });

    if (result.success) {
        // Update local memory
        if (appConfig) {
            if (!appConfig.settings) appConfig.settings = {};
            appConfig.settings.prompt_templates = list;
        }
        closePromptTemplateForm();
        updateSinglePromptTemplateDropdown();
        await renderPromptTemplates();
    } else {
        alert("Save failed: " + result.error);
    }
}

async function deletePromptTemplate(id) {
    if (!confirm("Delete this prompt template?")) return;
    const list = getSavedPromptTemplates().filter(x => x.id !== id);

    const result = await pywebview.api.save_config({
        prompt_templates: list
    });

    if (result.success) {
        if (appConfig) {
            if (!appConfig.settings) appConfig.settings = {};
            appConfig.settings.prompt_templates = list;
        }
        updateSinglePromptTemplateDropdown();
        await renderPromptTemplates();
    } else {
        alert("Delete failed: " + result.error);
    }
}
