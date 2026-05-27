(() => {
  // --- Generate button ---
  const btn = document.getElementById('btn-generate');
  const spinner = document.getElementById('gen-spinner');
  const errEl = document.getElementById('gen-err');

  if (btn) {
    btn.addEventListener('click', async () => {
      errEl.textContent = '';
      spinner.classList.remove('hidden');
      btn.disabled = true;
      const kwCount = window.INTEL_KW_COUNT || 26;
      const messages = [
        `Analysing ${kwCount} keywords…`,
        'Extracting SERP features…',
        'Detecting featured snippets…',
        'Scanning PAA questions…',
        'Clustering PAA themes…',
        'Almost done…',
      ];
      let msgIdx = 0;
      spinner.textContent = messages[0];
      const msgTimer = setInterval(() => {
        msgIdx = Math.min(msgIdx + 1, messages.length - 1);
        spinner.textContent = messages[msgIdx];
      }, 12000);
      try {
        const resp = await fetch(window.GENERATE_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ force: !!window.INTEL_GENERATED }),
        });
        clearInterval(msgTimer);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        window.location.reload();
      } catch (err) {
        clearInterval(msgTimer);
        errEl.textContent = 'Error: ' + err.message;
        spinner.classList.add('hidden');
        btn.disabled = false;
      }
    });
  }

  // --- OVI category filter ---
  const oviTable = document.getElementById('ovi-table');
  document.querySelectorAll('.ovi-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.ovi-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.dataset.cat;
      if (!oviTable) return;
      oviTable.querySelectorAll('tbody tr').forEach(row => {
        row.style.display = (cat === 'ALL' || row.dataset.cat === cat) ? '' : 'none';
      });
      // Re-number visible rows
      let n = 1;
      oviTable.querySelectorAll('tbody tr').forEach(row => {
        if (row.style.display !== 'none') {
          row.querySelector('td').textContent = n++;
        }
      });
    });
  });

  // --- Copy all PAA questions ---
  const copyBtn = document.getElementById('btn-copy-paa');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const questions = Array.from(
        document.querySelectorAll('.paa-table tbody tr td:first-child')
      ).map(td => td.textContent.trim()).filter(Boolean);
      const text = questions.join('\n');
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;opacity:0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      const orig = copyBtn.textContent;
      copyBtn.textContent = 'Copied!';
      setTimeout(() => { copyBtn.textContent = orig; }, 1500);
    });
  }
})();
