var GCFG = JSON.parse(document.getElementById('landing-config').textContent).google;

var CLIENT_ID = GCFG.client_id;
var IS_PRODUCTION = location.hostname === GCFG.production_domain;
var HAS_GOOGLE_CLIENT = Boolean(CLIENT_ID);

if (IS_PRODUCTION && HAS_GOOGLE_CLIENT) {
  document.getElementById('googleSection').classList.remove('hidden');
  function handleGoogleCredential(response) {
    var errEl = document.getElementById('loginError');
    errEl.textContent = '';
    fetch('/api/auth/google', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({credential: response.credential})
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Google auth failed'); });
      return r.json();
    }).then(function(data) {
      if (data.ok) {
        window.location.reload();
      }
    }).catch(function(err) {
      errEl.textContent = err.message;
    });
  }
  try {
    if (typeof google !== 'undefined' && google.accounts) {
      google.accounts.id.initialize({client_id: CLIENT_ID, callback: handleGoogleCredential, cancel_on_tap_outside: false});
      google.accounts.id.renderButton(document.getElementById('googleButtonWrapper'), {type: 'standard', shape: 'rectangular', theme: 'outline', size: 'large', text: 'signin_with'});
      google.accounts.id.prompt();
    } else {
      throw new Error('GSI not loaded');
    }
  } catch(e) {
    document.getElementById('googleButtonWrapper').innerHTML = '<a href="' + location.origin + '/api/auth/google?redirect=' + encodeURIComponent(location.href) + '" style="display:inline-flex;align-items:center;gap:8px;padding:10px 24px;border:1px solid #3A3226;border-radius:8px;color:#F1E4CE;text-decoration:none;font-size:14px;background:#1F1B14"><svg width="18" height="18" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3c-1.6 4.6-5.9 8-11.3 8-6.4 0-11.6-5.2-11.6-11.6S17.6 12.8 24 12.8c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6.7 29.4 4.5 24 4.5 12.7 4.5 3.5 13.7 3.5 25S12.7 45.5 24 45.5 44.5 36.3 44.5 25c0-1.6-.2-3.2-.5-4.7l-.4-.2z"/><path fill="#FF3D00" d="M4.9 14.7l6.6 4.9C13 15 18 12.8 24 12.8c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6.7 29.4 4.5 24 4.5 16.1 4.5 9.2 8.6 5.7 14.5l-.8.2z"/><path fill="#4CAF50" d="M24 45.5c5.5 0 10.5-2 14.3-5.3l-6.6-5.6c-2.2 1.5-5 2.4-7.7 2.4-5.5 0-10.2-3.6-11.8-8.6l-6.8 5.3C9.2 41.4 16.1 45.5 24 45.5z"/><path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.2 4.3-4.1 5.7l6.6 5.6c-.1.1 7.7-6 7.7-18.5 0-1.6-.2-3.2-.5-4.7l-.4-.1z"/></svg> Sign in with Google</a>';
  }
}

