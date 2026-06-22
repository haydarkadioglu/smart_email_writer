/* ==========================================================================
   analytics.js  –  Analytics tab logic
   ========================================================================== */

let currentAnalyticsPeriod = 'month';

// ── Load & Render ─────────────────────────────────────────────────────────
async function loadAnalytics(period) {
    currentAnalyticsPeriod = period || currentAnalyticsPeriod;

    // Update filter button states
    document.querySelectorAll('.analytics-period-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.period === currentAnalyticsPeriod);
    });

    const res = await pywebview.api.get_analytics({ period: currentAnalyticsPeriod });
    if (!res.success) {
        showFlash('flash-analytics', '✘ ' + res.error, true);
        return;
    }

    // ── Summary cards ─────────────────────────────────────────────────────
    setInner('analytics-total',   res.total);
    setInner('analytics-sent',    res.sent_ok);
    setInner('analytics-failed',  res.sent_failed);
    setInner('analytics-drafts-pending', '—'); // placeholder

    // ── Category chart ────────────────────────────────────────────────────
    renderCategoryChart(res.categories);

    // ── Daily activity bars ───────────────────────────────────────────────
    renderDailyChart(res.daily);
}

function setInner(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerText = val;
}

// ── Category bar chart (pure CSS) ─────────────────────────────────────────
function renderCategoryChart(categories) {
    const container = document.getElementById('analytics-categories');
    if (!container) return;

    const entries = Object.entries(categories).sort((a, b) => b[1] - a[1]);
    if (!entries.length) {
        container.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">No data for this period.</p>';
        return;
    }

    const max = Math.max(...entries.map(e => e[1]));
    container.innerHTML = entries.map(([cat, count]) => {
        const pct = max > 0 ? Math.round((count / max) * 100) : 0;
        return `
        <div class="analytics-bar-row">
            <div class="analytics-bar-label">${escapeHtml(cat)}</div>
            <div class="analytics-bar-track">
                <div class="analytics-bar-fill" style="width:${pct}%"></div>
            </div>
            <div class="analytics-bar-count">${count}</div>
        </div>`;
    }).join('');
}

// ── Daily activity sparkline ──────────────────────────────────────────────
function renderDailyChart(daily) {
    const container = document.getElementById('analytics-daily');
    if (!container) return;

    const entries = Object.entries(daily).sort((a, b) => a[0].localeCompare(b[0]));
    if (!entries.length) {
        container.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">No activity in this period.</p>';
        return;
    }

    const max = Math.max(...entries.map(e => e[1]), 1);
    container.innerHTML = `
    <div class="analytics-daily-chart">
        ${entries.map(([day, count]) => {
            const h = Math.max(4, Math.round((count / max) * 80));
            const label = day.slice(5); // MM-DD
            return `
            <div class="analytics-daily-col" title="${day}: ${count} emails">
                <div class="analytics-daily-bar" style="height:${h}px"></div>
                <div class="analytics-daily-label">${label}</div>
            </div>`;
        }).join('')}
    </div>`;
}

// ── CV upload helper (Profile tab) ────────────────────────────────────────
async function uploadAndParseCV() {
    const res = await pywebview.api.pick_files({ multiple: false, file_types: ['.pdf', '.docx', '.txt'] });
    if (!res || !res.length) return;

    const file_path = Array.isArray(res) ? res[0] : res;
    const btn = document.getElementById('btn-parse-cv');
    if (btn) { btn.disabled = true; btn.innerText = 'Parsing…'; }

    const result = await pywebview.api.parse_cv({ file_path });
    if (btn) { btn.disabled = false; btn.innerText = '📎 Upload CV & Auto-fill'; }

    if (!result.success) {
        showFlash('flash-profile', '✘ ' + result.error, true);
        return;
    }

    // Pre-fill profile form fields
    const p = result.profile;
    if (p.name)    setVal('profile-name',    p.name);
    if (p.email)   setVal('profile-email',   p.email);
    if (p.company) setVal('profile-company', p.company);
    if (p.role)    setVal('profile-role',    p.role);
    if (p.website) setVal('profile-website', p.website);
    // signature = summary
    if (p.summary) {
        const sig = document.getElementById('profile-signature');
        if (sig && !sig.value) sig.value = p.summary;
    }
    showFlash('flash-profile', '✔ Profile auto-filled from CV');
}

// ── Bind events ────────────────────────────────────────────────────────────
function bindAnalyticsEvents() {
    document.querySelectorAll('.analytics-period-btn').forEach(btn => {
        btn.addEventListener('click', () => loadAnalytics(btn.dataset.period));
    });
    const cvBtn = document.getElementById('btn-parse-cv');
    if (cvBtn) cvBtn.addEventListener('click', uploadAndParseCV);
}
