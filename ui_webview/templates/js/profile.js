/* ==========================================================================
   profile.js  –  Profile tab: form population, save, CV upload
   ========================================================================== */

function populateProfileForm() {
    const p = appConfig.profile || {};
    setVal('profile-name',      p.name      || '');
    setVal('profile-email',     p.email     || '');
    setVal('profile-company',   p.company   || '');
    setVal('profile-role',      p.role      || '');
    setVal('profile-website',   p.website   || '');
    setVal('profile-about-me',  p.about_me  || '');
    setVal('profile-signature', p.signature || '');
}

async function saveProfile() {
    const btn = document.getElementById('btn-save-profile');
    setBtnLoading(btn, true, "Saving...");
    const profileData = {
        name:      getVal('profile-name'),
        email:     getVal('profile-email'),
        company:   getVal('profile-company'),
        role:      getVal('profile-role'),
        website:   getVal('profile-website'),
        about_me:  getVal('profile-about-me'),
        signature: getVal('profile-signature'),
    };
    const result = await pywebview.api.save_config({
        profile: profileData
    });
    setBtnLoading(btn, false);
    if (result.success) {
        appConfig.profile = profileData;
    }
    showFlash('flash-profile', result.success ? '✔ Profile saved' : '✘ ' + result.error);
}

async function generateProfileFromChat() {
    const btn = document.getElementById('btn-generate-chat-summary');
    if (!btn) return;
    setBtnLoading(btn, true, "🧠 Summarizing...");

    const res = await pywebview.api.chat_generate_user_summary();
    setBtnLoading(btn, false);

    if (!res.success) {
        showFlash('flash-profile', '✘ ' + res.error, true);
        return;
    }

    const aboutMe = document.getElementById('profile-about-me');
    if (aboutMe) {
        aboutMe.value = res.summary;
        // Highlight feedback
        aboutMe.focus();
        aboutMe.style.borderColor = 'var(--accent-color)';
        setTimeout(() => {
            aboutMe.style.borderColor = '';
        }, 1500);
    }
    showFlash('flash-profile', '✔ Summary generated from chat! Don\'t forget to Save.');
}
