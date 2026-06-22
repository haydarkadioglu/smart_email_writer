/* ==========================================================================
   profile.js  –  Profile tab: form population, save, CV upload
   ========================================================================== */

function populateProfileForm() {
    const p = appConfig.settings.profile || {};
    setVal('profile-name',      p.name      || '');
    setVal('profile-email',     p.email     || '');
    setVal('profile-company',   p.company   || '');
    setVal('profile-role',      p.role      || '');
    setVal('profile-website',   p.website   || '');
    setVal('profile-signature', p.signature || '');
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
