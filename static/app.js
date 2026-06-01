(() => {
  const runDate = window.RUN_DATE;
  const total = window.TOTAL_KW;

  // --- Tab switching ---
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.remove('hidden');
    });
  });

  // --- Ads summary row expand/collapse ---
  document.querySelectorAll('.ads-kw-row.has-ads').forEach(row => {
    row.addEventListener('click', () => {
      const detail = document.getElementById('ads-detail-' + row.dataset.idx);
      if (detail) detail.classList.toggle('hidden');
    });
  });

  function renderAdsTab(idx, ads) {
    // Update summary row
    const summaryRow = document.querySelector(`.ads-kw-row[data-idx="${idx}"]`);
    if (!summaryRow) return;
    const offshore = (ads || []).filter(a => a.is_offshore).length;
    summaryRow.cells[1].textContent = ads.length || '—';
    summaryRow.cells[2].innerHTML = offshore
      ? `<span class="offshore-flag">⚠ ${offshore}</span>`
      : (ads.length ? '0' : '—');
    summaryRow.cells[3].className = 'dim';
    summaryRow.cells[3].textContent = ads.map(a => a.advertiser).join(', ') || '—';

    if (ads.length) {
      summaryRow.classList.add('has-ads');
      summaryRow.style.cursor = 'pointer';
    }

    // Rebuild or create detail row
    let detailRow = document.getElementById('ads-detail-' + idx);
    if (!detailRow) {
      detailRow = document.createElement('tr');
      detailRow.id = 'ads-detail-' + idx;
      detailRow.className = 'ads-detail-row hidden';
      summaryRow.after(detailRow);
      summaryRow.addEventListener('click', () => detailRow.classList.toggle('hidden'));
    }

    if (!ads.length) {
      detailRow.innerHTML = '';
      return;
    }

    const labels = window.CATEGORY_LABELS || {};
    const rows = ads.map(ad => {
      const dc = ad.domain_category || 'OTHER';
      const dcLabel = labels[dc] || dc;
      return `
      <tr>
        <td>${ad.position}</td>
        <td>${escapeHtml(ad.advertiser)}</td>
        <td><span class="cat-pill cat-${escapeHtml(dc)}">${escapeHtml(dcLabel)}</span></td>
        <td class="dim"><a href="${escapeHtml(ad.landing_url)}" target="_blank" rel="noopener">${escapeHtml(ad.display_url || ad.landing_url)}</a></td>
        <td>${escapeHtml(ad.ad_position)}</td>
        <td>${ad.is_offshore ? '<span class="offshore-flag">YES ⚠</span>' : 'no'}</td>
        <td class="dim">${escapeHtml(ad.notes)}</td>
      </tr>`;
    }).join('');

    detailRow.innerHTML = `<td colspan="4">
      <table class="ads-detail-table">
        <thead><tr><th>#</th><th>Advertiser</th><th>Type</th><th>Landing Page</th><th>Pos</th><th>Offshore</th><th>Notes</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></td>`;

    // Refresh tab badge
    updateAdsBadge();
  }

  function updateAdsBadge() {
    let totalAds = 0, totalOffshore = 0;
    document.querySelectorAll('.ads-kw-row').forEach(row => {
      const count = parseInt(row.cells[1].textContent, 10) || 0;
      totalAds += count;
      const offshoreEl = row.cells[2].querySelector('.offshore-flag');
      if (offshoreEl) totalOffshore += parseInt(offshoreEl.textContent.match(/\d+/)?.[0] || '0', 10);
    });
    const tabBtn = document.querySelector('.tab-btn[data-tab="ads"]');
    if (!tabBtn) return;
    let badge = tabBtn.querySelector('.ads-badge');
    if (totalAds === 0) { if (badge) badge.remove(); return; }
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'ads-badge';
      tabBtn.appendChild(badge);
    }
    badge.className = 'ads-badge ' + (totalOffshore >= 4 ? 'badge-red' : totalOffshore >= 1 ? 'badge-amber' : 'badge-blue');
    badge.textContent = totalOffshore > 0 ? `⚠ ${totalOffshore} offshore` : `${totalAds} ads`;
  }

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
        window.CATEGORIES.map(c => `<option value="${escapeHtml(c.key)}"${c.key === p.category ? ' selected' : ''}>${escapeHtml(c.label)}</option>`).join('')
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

  // --- PDF report download ---
  const pdfBtn = document.getElementById('btn-pdf-report');
  if (pdfBtn) {
    pdfBtn.addEventListener('click', async () => {
      const url = pdfBtn.dataset.url;
      const spinner = document.getElementById('pdf-spinner');
      const errEl = document.getElementById('pdf-err');
      errEl.textContent = '';
      spinner.classList.remove('hidden');
      pdfBtn.disabled = true;
      try {
        const resp = await fetch(url);
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          throw new Error(data.error || `HTTP ${resp.status}`);
        }
        const blob = await resp.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `AUS_Ads_Intelligence_${runDate}.pdf`;
        a.click();
        URL.revokeObjectURL(a.href);
      } catch (err) {
        errEl.textContent = 'Error: ' + err.message;
      } finally {
        spinner.classList.add('hidden');
        pdfBtn.disabled = false;
      }
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
        renderAdsTab(idx, data.ads || []);
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
