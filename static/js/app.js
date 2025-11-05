// Central JS for index and admin pages
(function(){
  // --- Common helpers ---
  function qs(sel){ return document.querySelector(sel); }
  function qsa(sel){ return Array.from(document.querySelectorAll(sel)); }

  // Alert helper
  // Toast helper
  function createToast(message, type='success', delay=4000){
    const container = qs('#toast-container');
    if(!container) return;
    const toastId = 'toast-' + Date.now();
    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-bg-' + (type==='danger' ? 'danger' : (type==='warning' ? 'warning' : (type==='info' ? 'info' : 'success'))) + ' border-0';
    toastEl.role = 'status';
    toastEl.ariaLive = 'polite';
    toastEl.ariaAtomic = 'true';
    toastEl.id = toastId;
    toastEl.style.minWidth = '200px';
    toastEl.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
    container.appendChild(toastEl);
    const bsToast = new bootstrap.Toast(toastEl, { delay: delay });
    bsToast.show();
    toastEl.addEventListener('hidden.bs.toast', ()=> toastEl.remove());
  }
  window.showAlert = createToast;

  // Index page behaviour
  async function initIndex(){
    const form = qs('#registerForm');
    if(form){
      const input = qs('#serialInput');
      const list = qs('#serialList');
      const registerBtn = qs('#registerBtn');
      const refreshBtn = qs('#refreshBtn');

      async function refreshList(){
        try{
          const res = await fetch('/api/list_serials');
          const data = await res.json();
          list.innerHTML = '';
          (data.serials || []).forEach(s => {
            const li = document.createElement('li');
            li.className = 'd-flex justify-content-between align-items-center py-2 px-2 mb-2 rounded';
            li.style.background = '#0b1116';
            li.innerHTML = `<span class="serial-text">${s}</span><button class="btn btn-sm btn-outline-danger delete-btn" data-serial="${s}">Delete</button>`;
            list.appendChild(li);
          });
          attachDeleteHandlers();
          checkAdmin();
        }catch(e){ console.error(e); }
      }

      form.addEventListener('submit', async (e)=>{
        e.preventDefault();
        const serial = input.value.trim(); if(!serial) return;
        registerBtn.disabled = true;
        try{
          const res = await fetch('/', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({serial}) });
          const data = await res.json();
          if(data.success){
            showAlert('Serial registered: ' + serial, 'success');
            const li = document.createElement('li');
            li.className = 'd-flex justify-content-between align-items-center py-2 px-2 mb-2 rounded';
            li.style.background = '#0b1116';
            li.innerHTML = `<span class="serial-text">${serial}</span><button class="btn btn-sm btn-outline-danger delete-btn" data-serial="${serial}">Delete</button>`;
            list.insertBefore(li, list.firstChild);
            input.value = '';
            attachDeleteHandlers();
          } else { showAlert('Serial already registered or invalid', 'warning'); }
        }catch(err){ console.error(err); showAlert('Error registering serial', 'danger'); }
        finally{ registerBtn.disabled = false; }
      });

      refreshBtn.addEventListener('click', refreshList);

      function filterList(){
        const q = qs('#searchInput').value.trim().toLowerCase();
        qsa('#serialList li').forEach(li => {
          const text = li.querySelector('.serial-text').textContent.toLowerCase();
          li.style.display = text.includes(q) ? '' : 'none';
        });
      }
      const searchInput = qs('#searchInput'); if(searchInput) searchInput.addEventListener('input', filterList);

      function attachDeleteHandlers(){
        qsa('.delete-btn').forEach(btn => {
          btn.onclick = async () => {
            const s = btn.getAttribute('data-serial');
            if(!confirm(`Delete serial ${s}?`)) return;
            try{
              const res = await fetch('/api/delete_serial', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({serial: s}) });
              const data = await res.json();
              if(data.success){ showAlert('Deleted: ' + s, 'info'); btn.closest('li').remove(); } else { showAlert('Not found or already deleted', 'warning'); }
            }catch(e){ console.error(e); showAlert('Error deleting serial', 'danger'); }
          };
        });
      }

      async function checkAdmin(){
        try{
          const res = await fetch('/api/is_admin'); const data = await res.json(); const visible = data.admin;
          qsa('.delete-btn').forEach(b=> b.style.display = visible ? '' : 'none');
          if(!visible){
            // do not show an Admin button to public users
            const ex = qs('#exportBtn'); if(ex) ex.remove();
            const lo = qs('#logoutBtn'); if(lo) lo.remove();
          }
          else { const el = qs('#adminBtn'); if(el) el.remove(); if(!qs('#exportBtn')){ const exp = document.createElement('a'); exp.id='exportBtn'; exp.className='btn btn-sm btn-outline-light ms-2'; exp.textContent='Export CSV'; exp.href='/export_csv'; document.querySelector('.navbar .d-flex').prepend(exp); } if(!qs('#logoutBtn')){ const l = document.createElement('button'); l.id='logoutBtn'; l.className='btn btn-sm btn-outline-danger ms-2'; l.textContent='Logout'; l.onclick = async ()=>{ await fetch('/logout',{method:'POST'}); location.reload(); }; document.querySelector('.navbar .d-flex').prepend(l); } }
        }catch(e){ console.error(e); }
      }

      attachDeleteHandlers();
      refreshList();
    }
  }

  // Admin page behaviour
  async function initAdmin(){
    if(!qs('#adminArea')) return;
    let adminState = { page: 1, per_page: 20, q: '' };

    async function loadAdmin(){
      const res = await fetch('/api/is_admin'); const info = await res.json(); if(!info.admin){ renderLogin(); return; } renderControls();
    }

    function renderLogin(){
      qs('#adminArea').innerHTML = '';
      qs('#adminLoginArea').innerHTML = `<div class="mb-3"><input id="pwd" class="form-control" placeholder="Admin password"></div><button id="loginBtn" class="btn btn-primary">Login</button>`;
      qs('#loginBtn').onclick = async ()=>{ const pwd=qs('#pwd').value; const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pwd})}); const j=await r.json(); if(j.success) loadAdmin(); else alert('Wrong password'); };
    }

    async function renderControls(){
      const params = new URLSearchParams({ q: adminState.q || '', page: adminState.page, per_page: adminState.per_page });
      const listRes = await fetch('/api/admin/serials?' + params.toString()); if(listRes.status===403){ renderLogin(); return; }
      const listJson = await listRes.json();
      const serials = listJson.serials || [];
      const total = listJson.total || 0;
      const page = listJson.page || 1;
      const per_page = listJson.per_page || adminState.per_page;

      // Fill the table body
      const tbody = qs('#admin-table-body');
      if(!tbody) return;
      tbody.innerHTML = '';
      serials.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><input class="row-check" type="checkbox" data-serial="${s}" /></td>
          <td class="serial-cell">${s}</td>
          <td><button class="btn btn-sm btn-danger single-delete" data-serial="${s}">Delete</button></td>
        `;
        tbody.appendChild(tr);
      });

      // single-delete handlers
      qsa('.single-delete').forEach(btn => btn.addEventListener('click', async (e) => {
        const s = btn.dataset.serial;
        if(!confirm('Delete '+s+'?')) return;
        try{
          const r = await fetch('/api/delete_serial', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({serial: s}) });
          const j = await r.json();
          if(j.success) renderControls(); else alert('Delete failed');
        }catch(err){ console.error(err); alert('Error'); }
      }));

      // select-all
      const selectAll = qs('#select-all');
      if(selectAll){
        selectAll.checked = false;
        selectAll.onchange = ()=>{ const checked = selectAll.checked; qsa('.row-check').forEach(ch=> ch.checked = checked); };
      }

      // delete selected - remove old handler first
      const deleteBtn = qs('#delete-selected');
      if(deleteBtn){
        const newBtn = deleteBtn.cloneNode(true);
        deleteBtn.parentNode.replaceChild(newBtn, deleteBtn);
        newBtn.addEventListener('click', async ()=>{
          const checked = qsa('.row-check').filter(c=> c.checked);
          if(checked.length === 0){ alert('No rows selected'); return; }
          if(!confirm(`Delete ${checked.length} selected serial(s)?`)) return;
          const toDelete = checked.map(c=> c.dataset.serial);
          let successCount = 0;
          for(const s of toDelete){
            try{ 
              const r = await fetch('/api/delete_serial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({serial:s})}); 
              const j = await r.json(); 
              if(j.success) successCount++; 
            }catch(e){ console.error(e); }
          }
          showAlert(`Deleted ${successCount} of ${toDelete.length}`, successCount > 0 ? 'success' : 'warning');
          renderControls();
        });
      }

      // refresh - remove old handler first
      const refreshBtn = qs('#refreshBtn');
      if(refreshBtn){
        const newRefresh = refreshBtn.cloneNode(true);
        refreshBtn.parentNode.replaceChild(newRefresh, refreshBtn);
        newRefresh.addEventListener('click', ()=> renderControls());
      }

      renderPagination(total, page, per_page);
      qs('#export-link').href = '/export_csv?' + new URLSearchParams({ q: adminState.q });
    }

    function renderPagination(total, page, per_page){
      const totalPages = Math.max(1, Math.ceil(total / per_page));
      const ul = qs('#pagination-controls'); ul.innerHTML = '';
      const makeLi = (label, p, disabled=false, active=false) => {
        const li = document.createElement('li'); li.className = 'page-item' + (disabled ? ' disabled' : '') + (active ? ' active' : ''); const a = document.createElement('a'); a.className='page-link'; a.href='#'; a.textContent=label; a.addEventListener('click',(e)=>{ e.preventDefault(); if(!disabled && page!==p){ adminState.page=p; renderControls(); }}); li.appendChild(a); return li; };
      ul.appendChild(makeLi('«', 1, page===1)); const start = Math.max(1, page-2); const end = Math.min(totalPages, page+2); for(let p=start;p<=end;p++){ ul.appendChild(makeLi(p,p,false,p===page)); } ul.appendChild(makeLi('»', totalPages, page===totalPages));
    }

    document.getElementById('admin-search')?.addEventListener('input', (e)=>{ adminState.q = e.target.value; adminState.page=1; renderControls(); });
    document.getElementById('per-page')?.addEventListener('change', (e)=>{ adminState.per_page = parseInt(e.target.value,10)||20; adminState.page=1; renderControls(); });

    // --- Admin additional features: tabs, activations, api keys ---
    // Tab switching: handled by admin.html nav tabs
    qsa('#adminTabs .nav-link').forEach(a=> a.addEventListener('click', (e)=>{
      e.preventDefault(); qsa('#adminTabs .nav-link').forEach(x=> x.classList.remove('active')); a.classList.add('active');
      const t = a.getAttribute('data-tab'); qsa('#adminArea > div').forEach(d=> d.style.display='none'); const sel = qs('#tab-'+t); if(sel) sel.style.display='block';
      if(t==='activations') loadActivations(); if(t==='api_keys') loadApiKeys(); if(t==='serials') renderControls();
    }));

    async function loadActivations(){
      const el = qs('#activationsList'); if(!el) return; el.textContent='Loading...';
      try{
        const r = await fetch('/api/admin/activations'); if(r.status===403){ el.textContent='Login required'; return; }
        const j = await r.json(); const rows = j.activations || [];
  if(rows.length===0){ el.textContent='No activations'; return; }
  el.innerHTML = rows.map(a=> `<div class="py-2" style="border-bottom:1px solid rgba(255,255,255,0.03)"><strong>${a.serial}</strong> (${a.model}) - ${a.status} - ${a.reason} <br><small class="muted">${a.created_at} via ${a.api_key_user||'unknown'}</small></div>`).join('');
      }catch(e){ console.error(e); el.textContent='Error loading activations'; }
    }

    async function loadApiKeys(){
      const el = qs('#apiKeysList'); if(!el) return; el.textContent='Loading...';
      try{
        const r = await fetch('/api/admin/api_keys'); if(r.status===403){ el.textContent='Login required'; return; }
        const j = await r.json(); const rows = j.api_keys || [];
        if(rows.length===0){ el.textContent='No API keys'; return; }
        el.innerHTML = rows.map(k=> `<div class="d-flex justify-content-between align-items-center py-2" style="border-bottom:1px solid rgba(255,255,255,0.03)"><div><strong>${k.label}</strong> <small class="muted">${k.scope}</small><br><small class="muted">${k.key.slice(0,12)}... created ${k.created_at}</small></div><div><button class="btn btn-sm btn-secondary toggle-key" data-key="${k.key}">${k.active? 'Disable':'Enable'}</button></div></div>`).join('');
        qsa('.toggle-key').forEach(b=> b.onclick = async ()=>{ const k=b.dataset.key; try{ const rr = await fetch('/api/admin/api_keys/'+k+'/toggle',{method:'POST'}); const jj = await rr.json(); if(jj.success) loadApiKeys(); else alert('Toggle failed'); }catch(e){ alert('Error'); } });
      }catch(e){ console.error(e); el.textContent='Error loading keys'; }
    }

    qs('#createApiBtn')?.addEventListener('click', async ()=>{
      const label = qs('#newApiLabel').value.trim(); const scope = qs('#newApiScope').value;
      if(!label) return alert('Enter label');
      try{ const r = await fetch('/api/admin/api_keys', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ label, scope }) }); const j = await r.json(); if(r.ok && j.success){ alert('Created key: '+j.key); qs('#newApiLabel').value=''; loadApiKeys(); } else { alert('Error creating key: '+(j.message||'unknown')); } }catch(e){ alert('Error'); }
    });

    loadAdmin();
  }

  // Hero quick-register handler (for /home)
  (function(){
    const heroForm = qs('#heroRegister');
    if(!heroForm) return;
    heroForm.addEventListener('submit', async (e)=>{
      e.preventDefault();
      const input = qs('#heroSerial');
      const btn = qs('#heroRegisterBtn');
      const spinner = qs('#heroSpinner');
      const serial = input.value.trim(); if(!serial) return;
      const tx = (qs('#heroTx') || {}).value ? qs('#heroTx').value.trim() : '';
      btn.disabled = true;
      if(spinner) spinner.style.display = '';
      try{
        // send payment record first
  const chain = (qs('#heroChain') || {}).value || 'bsc';
  // if chain is 'free' we don't require a tx
  if(chain !== 'free'){
    // basic tx hash validation: expect 0x-prefixed hex or at least 10 chars
    if(tx && !(/^0x[0-9a-fA-F]{6,}$/).test(tx) && tx.length < 10){
      createToast('Please paste a valid TX hash (or a full TX link)', 'warning');
      return;
    }
    if(!tx){ createToast('TX hash is required for paid registrations', 'warning'); return; }
  }
  const payRes = await fetch('/pay_register', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ serial, tx, amount:5.0, currency:'USDT', chain }) });
        const payJson = await payRes.json();
        if(!payRes.ok || !payJson.success){
          const msg = (payJson && (payJson.message || payJson.error)) ? (payJson.message || payJson.error) : 'failed';
          createToast('Payment error: ' + msg, 'danger');
        } else {
          const pid = payJson.payment_id;
          const pchain = payJson.chain || chain || 'bsc';
          createToast(`Payment recorded (#${pid}) on ${pchain.toUpperCase()}, awaiting admin verification`, 'info');
          input.value=''; if(qs('#heroTx')) qs('#heroTx').value='';
          // show brief details under form
          let details = qs('#heroSuccess');
          if(!details){ details = document.createElement('div'); details.id='heroSuccess'; details.className='mt-2 text-success small'; qs('#heroRegister').appendChild(details); }
          details.textContent = `Saved: id=${pid} serial=${serial} chain=${pchain.toUpperCase()}`;
        }
      }catch(err){ console.error(err); createToast('Error submitting payment', 'danger'); }
      finally{ btn.disabled = false; if(spinner) spinner.style.display = 'none'; }
    });
  })();

  // auto-extract tx hash when user pastes a full explorer link into hero TX input
  (function(){
    const txInput = qs('#heroTx');
    if(!txInput) return;
    txInput.addEventListener('change', ()=>{
      const v = (txInput.value || '').trim();
      if(!v) return;
      // try to find 0x... hex inside string
      const m = v.match(/(0x[a-fA-F0-9]{6,})/);
      if(m && m[1]){ txInput.value = m[1]; return; }
      // try to extract after /tx/ in urls
      const m2 = v.match(/\/tx\/(0x[a-fA-F0-9]{6,})/i);
      if(m2 && m2[1]){ txInput.value = m2[1]; return; }
    });
  })();

  // Recent payments loader for home
    // copy payment address
    const copyBtn = qs('#copyPaymentAddr');
    if(copyBtn){
      copyBtn.addEventListener('click', async ()=>{
        const addr = qs('#paymentAddr')?.textContent || '';
  try{ await navigator.clipboard.writeText(addr); createToast('Payment address copied', 'info'); }catch(e){ createToast('Copy failed - select and copy manually', 'warning'); }
      });
    }
  async function loadRecentPayments(){
    const el = qs('#recentPayments'); if(!el) return;
    try{
      const res = await fetch('/api/recent_payments?limit=8');
      const j = await res.json();
      const rows = j.payments || [];
      if(rows.length===0){ el.textContent = 'No recent payments'; return; }
      el.innerHTML = rows.map(p=>{
        const tx = p.tx || '';
        const safeTx = (typeof tx === 'string' && tx.length>6) ? tx : 'n/a';
        const txLink = (p.chain && p.chain.toLowerCase()==='bsc' && tx.startsWith('0x')) ? `https://bscscan.com/tx/${tx}` : (p.chain && p.chain.toLowerCase()==='eth' && tx.startsWith('0x') ? `https://etherscan.io/tx/${tx}` : '#');
        const txHtml = txLink === '#' ? `<span class="muted">${safeTx}</span>` : `<a href="${txLink}" target="_blank" rel="noopener">${safeTx.slice(0,12)}...</a>`;
  return `<div style="border-bottom:1px solid rgba(255,255,255,0.03); padding:6px 0"><strong>${p.serial}</strong> - ${p.amount} ${p.currency} • ${txHtml} • <em>${p.status}</em></div>`;
      }).join('');
    }catch(e){ console.error(e); el.textContent = 'Error loading payments'; }
  }
  document.addEventListener('DOMContentLoaded', ()=>{ setTimeout(loadRecentPayments, 500); });

  // Admin payments loader
  async function loadAdminPayments(){
    const area = qs('#paymentsArea'); if(!area) return;
    try{
      const res = await fetch('/api/admin/payments');
      if(res.status===403){ area.innerHTML = '<div class="muted">Login to see payments</div>'; return; }
      const j = await res.json();
      const payments = j.payments || [];
      if(payments.length===0){ area.innerHTML = '<div class="muted">No payments</div>'; return; }
  const rows = payments.map(p=> `<div class="d-flex justify-content-between align-items-center py-2" style="border-bottom:1px solid rgba(255,255,255,0.03)"><div><strong>${p.serial}</strong><br><small class="muted">${p.tx} • ${p.amount} ${p.currency} • ${p.status}</small></div><div class="d-flex gap-2 align-items-center"><select class="form-select form-select-sm chain-select" data-id="${p.id}"><option value="eth">ETH (Etherscan)</option><option value="bsc">BSC (BscScan)</option></select><button class="btn btn-sm btn-success verify-pay" data-id="${p.id}">Verify</button></div></div>`).join('');
      area.innerHTML = rows;
      qsa('.verify-pay').forEach(b=> b.onclick = async ()=>{
        const id = b.dataset.id; const sel = document.querySelector('.chain-select[data-id="'+id+'"]'); const chain = sel ? sel.value : 'eth';
        if(!confirm('Auto-verify payment '+id+' on '+chain+'?')) return;
        try{ const r = await fetch('/api/auto_verify', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ payment_id: parseInt(id,10), chain }) }); const jr = await r.json(); if(r.ok && jr.success) { createToast('Payment auto-verified', 'success'); loadAdminPayments(); } else { createToast('Auto verify failed: '+(jr.message||'error'), 'danger'); } }catch(e){ console.error(e); createToast('Error auto-verifying', 'danger'); }
      });
      // cleanup button handler (marks obviously-bad payments as invalid)
      const cleanupBtn = qs('#cleanupPaymentsBtn');
      if(cleanupBtn){
        cleanupBtn.onclick = async ()=>{
          if(!confirm('Run cleanup to mark obviously-bad payments as invalid?')) return;
          try{
            const r = await fetch('/api/admin/cleanup_bad_payments', { method: 'POST' });
            const j = await r.json();
            const marked = j.marked || j.marked_invalid || 0;
            createToast('Cleanup complete, marked: ' + marked, 'info');
            loadAdminPayments();
          }catch(e){ console.error(e); createToast('Cleanup failed', 'danger'); }
        };
      }
    }catch(e){ console.error(e); area.innerHTML = '<div class="muted">Error loading</div>'; }
  }

  // Initialize based on page
  document.addEventListener('DOMContentLoaded', ()=>{ 
    initIndex();
    initAdmin();
    setTimeout(()=>{ loadAdminPayments(); }, 800); 
  });

  // listen for custom toast events dispatched from templates
  document.addEventListener('show-toast', (e)=>{
    try{ const d = e.detail || {}; createToast(d.message || 'Notice', d.type || 'info'); }catch(err){ console.error(err); }
  });

})();
