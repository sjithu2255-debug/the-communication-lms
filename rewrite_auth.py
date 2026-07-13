import re

with open('index.html', 'r') as f:
    content = f.read()

# 1. Replace the old hashing and localStorage functions
# Let's locate them precisely.
new_auth_block = """/* ---------- Firebase Auth & Firestore Sync ---------- */
async function loadProgressFor(email){
  try {
    const docSnap = await window.getDoc(window.doc(window.db, "users", email));
    if (docSnap.exists()){
      const p = docSnap.data();
      return { mastered: p.mastered || [], attempts: p.attempts || {} };
    }
  } catch(e){ console.error(e); }
  return { mastered: [], attempts: {} };
}

async function saveProgress(){
  if (!auth.currentUser) return;
  try {
    await window.updateDoc(window.doc(window.db, "users", auth.currentUser), {
      mastered: progress.mastered,
      attempts: progress.attempts
    });
  } catch(e){ console.error(e); }
}

async function attemptAuth(rawEmail, password){
  const email = String(rawEmail || '').trim().toLowerCase();
  if (!email || !password){ state.authError = 'Enter both an email and a password.'; render(); return; }
  if (!email.endsWith('@searce.com')){ state.authError = 'Please use a @searce.com email address.'; render(); return; }
  if (password.length < 4){ state.authError = 'Password should be at least 4 characters.'; render(); return; }
  state.authError = null; state.authBusy = true; render();
  
  try {
    await window.signInWithEmailAndPassword(window.fbAuth, email, password);
  } catch(e) {
    if (e.code === 'auth/invalid-credential') {
      try {
        await window.createUserWithEmailAndPassword(window.fbAuth, email, password);
        await window.setDoc(window.doc(window.db, "users", email), {
          email: email,
          status: email === 'jithu.sreekumar@searce.com' ? 'approved' : 'pending',
          createdAt: Date.now(),
          mastered: [],
          attempts: {}
        });
      } catch(createErr) {
        if (createErr.code === 'auth/email-already-in-use') {
          state.authBusy = false;
          state.authError = "Incorrect password.";
          render();
        } else {
          state.authBusy = false;
          state.authError = 'Could not sign in or sign up. ' + createErr.message;
          render();
        }
      }
    } else {
      state.authBusy = false;
      state.authError = e.message || 'Something went wrong. Please try again.';
      render();
    }
  }
}

function handleAuthSubmit(e){
  e.preventDefault();
  const email = document.getElementById('auth-email').value;
  const password = document.getElementById('auth-password').value;
  state.authEmailDraft = email;
  attemptAuth(email, password);
  return false;
}

async function logout(){
  await window.signOut(window.fbAuth);
}

function init(){
  window.fbAuth.onAuthStateChanged(async (user) => {
    if (user) {
      const email = user.email;
      auth.currentUser = email;
      
      const userDoc = await window.getDoc(window.doc(window.db, "users", email));
      if (!userDoc.exists()) {
        await window.setDoc(window.doc(window.db, "users", email), {
          email: email,
          status: email === 'jithu.sreekumar@searce.com' ? 'approved' : 'pending',
          createdAt: Date.now(),
          mastered: [],
          attempts: {}
        });
      }
      
      progress = await loadProgressFor(email);
      
      if (email === 'jithu.sreekumar@searce.com') {
        state.view = 'admin_loading';
        render();
        loadAdminData();
      } else {
        const udata = (await window.getDoc(window.doc(window.db, "users", email))).data();
        const userStatus = udata?.status || 'pending';
        state.view = (userStatus === 'pending') ? 'pending' : (userStatus === 'rejected' ? 'rejected' : 'home');
        render();
      }
      state.authBusy = false;
      state.authNote = null;
    } else {
      auth.currentUser = null;
      progress = { mastered: [], attempts: {} };
      state.view = 'auth';
      render();
    }
  });
}

async function loadAdminData() {
  try {
    const snap = await window.getDocs(window.collection(window.db, "users"));
    const users = [];
    snap.forEach(doc => users.push(doc.data()));
    state.adminUsersData = users;
    state.view = 'admin';
    render();
  } catch(e) {
    console.error(e);
    state.authError = "Failed to load admin data";
    state.view = 'auth';
    render();
  }
}"""

content = re.sub(r'/\* ---------- password hashing.*?function render\(\)\{', new_auth_block + '\nfunction render(){', content, flags=re.DOTALL)

# 2. Modify renderAdmin
render_admin_start = "function renderAdmin() {"
render_admin_end = "window.removeUser = async function(email) {"

new_render_admin = """function renderAdmin() {
  if (state.view === 'admin_loading') {
    return `<div class="app-shell" style="align-items:center; justify-content:center; color:var(--paper-dim);">Loading data...</div>`;
  }
  const usersDataRaw = state.adminUsersData || [];
  let activeLearners = 0;
  let totalProgressPct = 0;
  let usersData = [];

  usersDataRaw.forEach(u => {
    const masteredCount = (u.mastered || []).length;
    const triedCount = Object.keys(u.attempts || {}).length;
    
    if (masteredCount > 0 || triedCount > 0) activeLearners++;

    let pct = Math.round((masteredCount / TOPICS.length) * 100) || 0;
    if (pct > 100) pct = 100;
    totalProgressPct += pct;

    usersData.push({
      email: u.email,
      mastered: masteredCount,
      tried: triedCount,
      pct: pct,
      status: u.status || 'approved'
    });
  });

  usersData.sort((a,b) => b.pct - a.pct);
  const avgPct = usersData.length ? Math.round(totalProgressPct / usersData.length) + '%' : '0%';
  
  let tbodyHTML = '';
  if (usersData.length === 0) {
    tbodyHTML = '<tr><td colspan="5"><div style="text-align:center; padding:40px; color:var(--paper-dim);">No users found.</div></td></tr>';
  } else {
    tbodyHTML = usersData.map(u => `
      <tr class="admin-tr">
        <td class="admin-td">
          <div style="font-weight:600; color:var(--paper);">${escapeHtml(u.email)}</div>
        </td>
        <td class="admin-td">
          <div style="font-size:13px; margin-bottom:4px;">${u.pct}% Mastered</div>
          <div style="height:8px; background:var(--line); border-radius:4px; overflow:hidden;">
            <div style="height:100%; width:${u.pct}%; background:linear-gradient(90deg, var(--good), var(--preps)); border-radius:4px;"></div>
          </div>
        </td>
        <td class="admin-td">
          <span style="display:inline-block; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:600; background:rgba(63,174,122,0.15); color:var(--good); margin-right:4px;">${u.mastered} Mastered</span>
          <span style="display:inline-block; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:600; background:var(--line); color:var(--paper-dim);">${u.tried} Tried</span>
        </td>
        <td class="admin-td" style="color:var(--paper-dim); font-size:13px;">
          ${u.status === 'pending' ? `<button class="auth-btn" style="padding:6px 12px; font-size:12px; background:var(--accent3); border:none; border-radius:8px; cursor:pointer; font-weight:600; color:#fff; margin-right:6px;" onclick="approveUser('${escapeHtml(u.email)}')">Approve</button><button class="auth-btn" style="padding:6px 12px; font-size:12px; background:rgba(224,101,74,0.15); color:#F5A38A; border:1px solid rgba(224,101,74,0.3); border-radius:8px; cursor:pointer; font-weight:600;" onclick="rejectUser('${escapeHtml(u.email)}')">Reject</button>` : (u.status === 'rejected' ? '<span style="color:#F5A38A; font-weight:600;">Rejected</span>' : ((u.mastered > 0 || u.tried > 0) ? '<span style="color:var(--good); font-weight:600;">Active</span>' : 'Not started'))}
        </td>
        <td class="admin-td" style="text-align:right;">
          <button class="auth-btn" style="padding:6px 12px; font-size:12px; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); border-radius:8px; cursor:pointer; color:var(--paper); margin-right:6px;" onclick="viewUserProgress('${escapeHtml(u.email)}')">View Progress</button>
          <button class="auth-btn" style="padding:6px 12px; font-size:12px; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); border-radius:8px; cursor:pointer; color:var(--paper); margin-right:6px;" onclick="resetPassword('${escapeHtml(u.email)}')">Reset Pwd</button>
          ${u.email !== 'jithu.sreekumar@searce.com' ? `<button class="auth-btn" style="padding:6px 12px; font-size:12px; background:rgba(224,101,74,0.15); color:#F5A38A; border:1px solid rgba(224,101,74,0.3); border-radius:8px; cursor:pointer;" onclick="removeUser('${escapeHtml(u.email)}')">Remove</button>` : ''}
        </td>
      </tr>
    `).join('');
  }

  return `
    <div class="app-shell">
      <div class="topbar">
        <div class="brand">Admin Dashboard</div>
        <div class="account-bar" style="max-width:none; padding:0; border:none; margin:0; display:block;"><button class="logout-btn" onclick="logout()">Log out</button></div>
      </div>
      <div style="padding:40px 24px; max-width:860px; margin:0 auto; width:100%;">
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:20px; margin-bottom:40px;">
          <div style="background:rgba(255,255,255,0.08); backdrop-filter:blur(22px) saturate(160%); -webkit-backdrop-filter:blur(22px) saturate(160%); border:1px solid rgba(255,255,255,0.16); border-radius:16px; padding:24px; text-align:center;">
            <h3 style="margin:0 0 10px 0; font-size:36px; font-family:'Fredoka',sans-serif; color:var(--paper);">${usersData.length}</h3>
            <p style="margin:0; color:var(--paper-dim); font-size:14px; text-transform:uppercase; letter-spacing:1px;">Total Users</p>
          </div>
          <div style="background:rgba(255,255,255,0.08); backdrop-filter:blur(22px) saturate(160%); -webkit-backdrop-filter:blur(22px) saturate(160%); border:1px solid rgba(255,255,255,0.16); border-radius:16px; padding:24px; text-align:center;">
            <h3 style="margin:0 0 10px 0; font-size:36px; font-family:'Fredoka',sans-serif; color:var(--paper);">${activeLearners}</h3>
            <p style="margin:0; color:var(--paper-dim); font-size:14px; text-transform:uppercase; letter-spacing:1px;">Active Learners</p>
          </div>
          <div style="background:rgba(255,255,255,0.08); backdrop-filter:blur(22px) saturate(160%); -webkit-backdrop-filter:blur(22px) saturate(160%); border:1px solid rgba(255,255,255,0.16); border-radius:16px; padding:24px; text-align:center;">
            <h3 style="margin:0 0 10px 0; font-size:36px; font-family:'Fredoka',sans-serif; color:var(--paper);">${avgPct}</h3>
            <p style="margin:0; color:var(--paper-dim); font-size:14px; text-transform:uppercase; letter-spacing:1px;">Avg Progress</p>
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.08); backdrop-filter:blur(22px) saturate(160%); -webkit-backdrop-filter:blur(22px) saturate(160%); border:1px solid rgba(255,255,255,0.16); border-radius:16px; overflow:hidden;">
          <table style="width:100%; border-collapse:collapse; text-align:left;">
            <thead>
              <tr>
                <th class="admin-th">User</th>
                <th class="admin-th">Progress</th>
                <th class="admin-th">Topics State</th>
                <th class="admin-th">Status</th>
                <th class="admin-th" style="text-align:right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${tbodyHTML}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}"""

content = re.sub(r'function renderAdmin\(\)\s*\{.*?window\.removeUser = async function\(email\)\s*\{', new_render_admin + '\nwindow.removeUser = async function(email) {', content, flags=re.DOTALL)

# 3. Modify window actions
remove_user_start = "window.removeUser = async function(email) {"
render_admin_progress = "function renderAdminUserProgress() {"

new_window_actions = """window.removeUser = async function(email) {
  if (email === 'jithu.sreekumar@searce.com') return;
  if (confirm('Are you sure you want to completely remove this user?')) {
    await window.deleteDoc(window.doc(window.db, "users", email));
    loadAdminData();
  }
};

window.approveUser = async function(email) {
  await window.updateDoc(window.doc(window.db, "users", email), { status: 'approved' });
  loadAdminData();
};

window.rejectUser = async function(email) {
  await window.updateDoc(window.doc(window.db, "users", email), { status: 'rejected' });
  loadAdminData();
};

window.resetPassword = async function(email) {
  if (confirm(`Send password reset email to ${email}?`)) {
    try {
      await window.sendPasswordResetEmail(window.fbAuth, email);
      alert(`Password reset email sent to ${email}.`);
    } catch(e) {
      alert("Error sending password reset email: " + e.message);
    }
  }
};

window.viewUserProgress = function(email) {
  state.selectedUser = email;
  state.view = 'admin_user_progress';
  render();
};

"""

content = re.sub(r'window\.removeUser = async function\(email\) \{.*?function renderAdminUserProgress\(\)\s*\{', new_window_actions + 'function renderAdminUserProgress() {', content, flags=re.DOTALL)

# 4. Modify renderAdminUserProgress
admin_progress_start = "function renderAdminUserProgress() {"
render_auth = "function renderAuth(){"

new_admin_progress = """function renderAdminUserProgress() {
  const email = state.selectedUser;
  const user = state.adminUsersData.find(u => u.email === email) || {};
  let rows = DATA.topics.map(t => {
    const attempts = user.attempts || {};
    const mastered = user.mastered || [];
    const p = attempts[t.id] || 0;
    const isMastered = mastered.includes(t.id);
    const statusText = isMastered ? '<span style="color:var(--good); font-weight:600;">Mastered (10/10)</span>' : (p > 0 ? `<span style="color:var(--connectors); font-weight:600;">Tried (Score: ${p})</span>` : '<span style="color:var(--paper-dim);">Not started</span>');
    return `
      <tr class="admin-tr">
        <td class="admin-td" style="font-weight:600; color:var(--paper);">${escapeHtml(t.title)}</td>
        <td class="admin-td">${statusText}</td>
      </tr>
    `;
  }).join('');

  return `
    <div class="app-shell">
      <div class="thread-header">
        <button class="back-btn" onclick="state.view='admin'; render();">←</button>
        <div>
          <div class="thread-title">Progress for ${escapeHtml(email)}</div>
          <div class="thread-persona">${escapeHtml(user.name || '')}</div>
        </div>
      </div>
      <div style="padding:40px 24px; max-width:860px; margin:0 auto; width:100%;">
        <div style="background:rgba(255,255,255,0.08); backdrop-filter:blur(22px) saturate(160%); -webkit-backdrop-filter:blur(22px) saturate(160%); border:1px solid rgba(255,255,255,0.16); border-radius:16px; overflow:hidden;">
          <table style="width:100%; border-collapse:collapse; text-align:left;">
            <thead>
              <tr>
                <th class="admin-th">Topic</th>
                <th class="admin-th">Status</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}
"""

content = re.sub(r'function renderAdminUserProgress\(\)\s*\{.*?function renderAuth\(\)\s*\{', new_admin_progress + 'function renderAuth(){', content, flags=re.DOTALL)

# 5. Add loadAdminData and renderAdminLoading into the render block if not there
render_block = """function render(){
  const app = document.getElementById('app');
  if (state.view === 'auth'){ app.innerHTML = renderAuth(); return; }
  if (state.view === 'home') app.innerHTML = renderHome();
  else if (state.view === 'pending') app.innerHTML = renderPending();
  else if (state.view === 'rejected') app.innerHTML = renderRejected();
  else if (state.view === 'admin' || state.view === 'admin_loading') app.innerHTML = renderAdmin();
  else if (state.view === 'admin_user_progress') app.innerHTML = renderAdminUserProgress();
"""
content = content.replace("else if (state.view === 'admin') app.innerHTML = renderAdmin();", "else if (state.view === 'admin' || state.view === 'admin_loading') app.innerHTML = renderAdmin();")

firebase_imports = """
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, onAuthStateChanged, sendPasswordResetEmail } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore, doc, setDoc, getDoc, collection, getDocs, updateDoc, onSnapshot, deleteDoc } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const firebaseConfig = {
  projectId: "communication-gym-lms",
  appId: "1:412865778031:web:16ee414e69f7ebe709d89a",
  storageBucket: "communication-gym-lms.firebasestorage.app",
  apiKey: "AIzaSyDKPJKZugeujdf9hNXI0na0LPUEbUaikFk",
  authDomain: "communication-gym-lms.firebaseapp.com",
  messagingSenderId: "412865778031",
  measurementId: "G-S3L57VNH7L",
};

const app = initializeApp(firebaseConfig);
const fbAuth = getAuth(app);
const db = getFirestore(app);

window.fbAuth = fbAuth;
window.db = db;
window.doc = doc;
window.setDoc = setDoc;
window.getDoc = getDoc;
window.collection = collection;
window.getDocs = getDocs;
window.updateDoc = updateDoc;
window.onSnapshot = onSnapshot;
window.deleteDoc = deleteDoc;
window.signInWithEmailAndPassword = signInWithEmailAndPassword;
window.createUserWithEmailAndPassword = createUserWithEmailAndPassword;
window.signOut = signOut;
window.sendPasswordResetEmail = sendPasswordResetEmail;
"""
content = re.sub(r'<script type="module">', '<script type="module">' + firebase_imports, content)

with open('index.html', 'w') as f:
    f.write(content)
