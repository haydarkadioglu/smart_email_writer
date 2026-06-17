/* ==========================================================================
   templates.js  –  Template CRUD & rendering
   ========================================================================== */

let editingTemplateId = null;

function bindTemplateEvents() {
    document.getElementById('btn-new-template').addEventListener('click', openNewTemplateForm);
    document.getElementById('btn-save-template-form').addEventListener('click', saveTemplateForm);
    document.getElementById('btn-cancel-template-form').addEventListener('click', closeTemplateForm);
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
