(() => {
  const runDate = window.RUN_DATE;
  const total = window.TOTAL_KW;

  function setProgress(done) {
    const pct = total ? (done / total) * 100 : 0;
    document.getElementById('bar-fill').style.width = pct + '%';
    document.getElementById('progress-text').textContent = `${done} / ${total} keywords processed`;
    const gen = document.getElementById('generate-link');
    if (done >= total) {
      gen.classList.remove('disabled');
      gen.removeAttribute('aria-disabled');
      gen.removeAttribute('tabindex');
    } else {
      gen.classList.add('disabled');
      gen.setAttribute('aria-disabled', 'true');
      gen.setAttribute('tabindex', '-1');
    }
  }

  function countProcessed() {
    return document.querySelectorAll('.kw-card .badge-processed').length;
  }

  function markProcessed(card) {
    const badge = card.querySelector('.kw-status');
    badge.classList.remove('badge-empty');
    badge.classList.add('badge-processed');
    badge.textContent = 'processed';
  }

  function renderRow(p) {
    const tr = document.createElement('tr');
    tr.dataset.rank = p.rank;
    tr.className = 'cat-' + (p.category || '');
    tr.innerHTML = `
      <td>${p.rank}</td>
      <td><input class="f-short-label" value="${escapeHtml(p.short_label || '')}"></td>
      <td class="f-domain" title="${escapeHtml(p.full_url || '')}">${escapeHtml(p.domain || '')}</td>
      <td><select class="f-category">${
        window.CATEGORIES.map(c => `<option value="${c}"${c === p.category ? ' selected' : ''}>${c}</option>`).join('')
      }</select></td>
      <td class="dim f-reasoning" title="${escapeHtml(p.reasoning || '')}">${escapeHtml(p.reasoning || '')}</td>
    `;
    return tr;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function renderWarnings(block, warnings) {
    block.innerHTML = '';
    (warnings || []).forEach(w => {
      const div = document.createElement('div');
      div.className = 'warning';
      const rank = w.rank ? `rank ${w.rank}: ` : '';
      div.innerHTML = `⚠ <strong>${escapeHtml(rank + (w.issue || ''))}</strong>${
        w.detail ? `<div class="dim">${escapeHtml(w.detail)}</div>` : ''
      }`;
      block.appendChild(div);
    });
  }

  function bindRowDirty(tr) {
    const onChange = () => tr.classList.add('dirty');
    tr.querySelectorAll('input, select').forEach(el => el.addEventListener('input', onChange));
    tr.querySelector('.f-category').addEventListener('change', e => {
      tr.className = 'cat-' + e.target.value;
      tr.classList.add('dirty');
    });
  }

  document.querySelectorAll('.btn-copy-kw').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const kw = btn.dataset.keyword || '';
      try {
        await navigator.clipboard.writeText(kw);
      } catch {
        const ta = document.createElement('textarea');
        ta.value = kw;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      const original = btn.textContent;
      btn.textContent = '✓ copied';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = original;
        btn.classList.remove('copied');
      }, 1200);
    });
  });

  document.querySelectorAll('.kw-card').forEach(card => {
    const idx = card.dataset.idx;
    const pasteEl = card.querySelector('.paste-input');
    const processBtn = card.querySelector('.btn-process');
    const saveBtn = card.querySelector('.btn-save');
    const spinner = card.querySelector('.spinner');
    const errEl = card.querySelector('.err-msg');
    const reviewTable = card.querySelector('.review-table');
    const tbody = reviewTable.querySelector('tbody');
    const saveRow = card.querySelector('.save-row');
    const saveStatus = card.querySelector('.save-status');
    const warningsBlock = card.querySelector('.warnings-block');

    tbody.querySelectorAll('tr').forEach(bindRowDirty);

    processBtn.addEventListener('click', async () => {
      const raw = pasteEl.value.trim();
      if (!raw) { errEl.textContent = 'Paste something first.'; return; }
      errEl.textContent = '';
      spinner.classList.remove('hidden');
      processBtn.disabled = true;
      try {
        const resp = await fetch(`/run/${runDate}/keyword/${idx}/process`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({raw_paste: raw}),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        tbody.innerHTML = '';
        (data.positions || []).forEach(p => {
          const tr = renderRow(p);
          tbody.appendChild(tr);
          bindRowDirty(tr);
        });
        renderWarnings(warningsBlock, data.warnings);
        reviewTable.classList.remove('hidden');
        saveRow.classList.remove('hidden');
        markProcessed(card);
        setProgress(countProcessed());
        saveStatus.textContent = '';
      } catch (err) {
        errEl.textContent = err.message;
      } finally {
        spinner.classList.add('hidden');
        processBtn.disabled = false;
      }
    });

    saveBtn.addEventListener('click', async () => {
      saveStatus.textContent = 'saving…';
      const positions = Array.from(tbody.querySelectorAll('tr')).map(tr => ({
        rank: parseInt(tr.dataset.rank, 10),
        short_label: tr.querySelector('.f-short-label').value,
        domain: tr.querySelector('.f-domain').textContent,
        full_url: tr.querySelector('.f-domain').title || '',
        category: tr.querySelector('.f-category').value,
        reasoning: tr.querySelector('.f-reasoning').title || tr.querySelector('.f-reasoning').textContent,
        edited: tr.classList.contains('dirty'),
      }));
      try {
        const resp = await fetch(`/run/${runDate}/keyword/${idx}/save`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({positions}),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        tbody.querySelectorAll('tr.dirty').forEach(tr => tr.classList.remove('dirty'));
        saveStatus.textContent = 'saved ✓';
        markProcessed(card);
        setProgress(countProcessed());
      } catch (err) {
        saveStatus.textContent = 'error: ' + err.message;
      }
    });
  });
})();
