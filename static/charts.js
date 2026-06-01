/* Phase 4 Dashboard — fetches /dashboard/data and renders the six sections.
   Chart.js is loaded from CDN in dashboard.html. */
(() => {
  if (!window.DASH_READY) return;

  const labels = window.CATEGORY_LABELS || {};
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  let healthChart, volChart, adsChart;

  async function load() {
    const range = $('range-select').value;
    const keyword = $('keyword-select').value;
    $('dash-loading').classList.remove('hidden');
    $('dash-error').textContent = '';
    try {
      const url = `${window.DASH_DATA_URL}?range=${encodeURIComponent(range)}&keyword=${encodeURIComponent(keyword)}`;
      const resp = await fetch(url);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
      $('dash-loading').classList.add('hidden');
      $('dash-body').classList.remove('hidden');
      render(data);
    } catch (err) {
      $('dash-loading').classList.add('hidden');
      $('dash-error').textContent = 'Error loading dashboard: ' + err.message;
    }
  }

  function render(d) {
    renderHostileAlert(d.health.alert);
    renderHealth(d.health, d.colours);
    renderEntrants(d.entrants);
    renderOVI(d.ovi);
    renderEMD(d.emd);
    renderVolatility(d.volatility);
    renderAds(d.ads);
  }

  // ── Banner ──
  function renderHostileAlert(alert) {
    const el = $('hostile-alert');
    if (!alert) { el.classList.add('hidden'); return; }
    el.classList.remove('hidden');
    el.innerHTML = `⚠ Hostile share up ${alert.delta_pp}pp this run ` +
      `(${alert.from_pct}% → ${alert.to_pct}%).`;
  }

  // ── Section 1 — stacked area ──
  function renderHealth(health, colours) {
    const cats = health.categories;
    const dates = health.series.map(s => s.run_date);
    const datasets = cats.map(cat => ({
      label: labels[cat] || cat,
      data: health.series.map(s => s.pct[cat] || 0),
      backgroundColor: (colours[cat] || '#ccc') + 'cc',
      borderColor: colours[cat] || '#ccc',
      borderWidth: 1,
      fill: true,
      pointRadius: 0,
      tension: 0.2,
    }));
    if (healthChart) healthChart.destroy();
    healthChart = new Chart($('chart-health'), {
      type: 'line',
      data: { labels: dates, datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          y: { stacked: true, max: 100, ticks: { callback: v => v + '%' }, title: { display: true, text: 'Share of results' } },
          x: { stacked: true },
        },
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } } },
      },
    });
    const last = health.series[health.series.length - 1];
    $('health-note').textContent = last
      ? `Latest run (${last.run_date}): ${last.hostile_pct}% hostile across ${last.total} classified results.`
      : '';
  }

  // ── Section 2 — new entrants table ──
  function renderEntrants(e) {
    const tbody = $('entrants-table').querySelector('tbody');
    const empty = $('entrants-empty');
    const sub = $('entrants-sub');
    tbody.innerHTML = '';
    if (!e.entrants || !e.entrants.length) {
      $('entrants-table').classList.add('hidden');
      empty.classList.remove('hidden');
      sub.textContent = '';
      return;
    }
    $('entrants-table').classList.remove('hidden');
    empty.classList.add('hidden');
    sub.textContent = `— ${e.entrants.length} domains across ${e.keyword_count} keywords (vs ${e.prev_run_date})`;
    tbody.innerHTML = e.entrants.map(r => `
      <tr class="${r.hostile ? 'row-hostile' : ''}">
        <td>${r.hostile ? '⚠ ' : ''}${esc(r.domain)}</td>
        <td><span class="cat-pill cat-${esc(r.category)}">${esc(r.category_label)}</span></td>
        <td>${esc(r.keyword)}</td>
        <td>#${esc(r.rank)}</td>
      </tr>`).join('');
  }

  // ── Section 3 — cross-run OVI ──
  function renderOVI(ovi) {
    const tbody = $('ovi-table').querySelector('tbody');
    const arrow = { up: '↑ up', down: '↓ down', stable: 'stable' };
    tbody.innerHTML = (ovi.domains || []).map(d => `
      <tr class="${d.hostile ? 'row-hostile' : ''}">
        <td>${d.hostile ? '⚠ ' : ''}${esc(d.domain)}</td>
        <td><span class="cat-pill cat-${esc(d.category)}">${esc(d.category_label)}</span></td>
        <td><strong>${d.runs_present}</strong>/${d.runs_total}</td>
        <td>${d.avg_keywords}</td>
        <td>${d.avg_pos}</td>
        <td class="trend-${d.trend}">${arrow[d.trend] || d.trend}</td>
        <td class="dim">${esc(d.first_seen)}</td>
      </tr>`).join('');
  }

  // ── Section 4 — EMD tables ──
  function renderEMD(emd) {
    const active = $('emd-active-table'), grave = $('emd-graveyard-table');
    const aBody = active.querySelector('tbody'), gBody = grave.querySelector('tbody');
    if (emd.active && emd.active.length) {
      active.classList.remove('hidden'); $('emd-active-empty').classList.add('hidden');
      aBody.innerHTML = emd.active.map(e => `
        <tr><td>${esc(e.domain)}</td><td>${esc(e.keyword)}</td><td>#${e.latest_position}</td>
        <td>${e.weeks_active}${e.weeks_active === 1 ? ' ← new' : ''}</td></tr>`).join('');
    } else {
      active.classList.add('hidden'); $('emd-active-empty').classList.remove('hidden');
    }
    if (emd.graveyard && emd.graveyard.length) {
      grave.classList.remove('hidden'); $('emd-graveyard-empty').classList.add('hidden');
      gBody.innerHTML = emd.graveyard.map(e => `
        <tr><td>${esc(e.domain)}</td><td class="dim">${esc(e.last_seen)}</td>
        <td>${e.weeks_active}</td><td>#${e.peak_position}</td></tr>`).join('');
    } else {
      grave.classList.add('hidden'); $('emd-graveyard-empty').classList.remove('hidden');
    }
  }

  // ── Section 5 — volatility bars ──
  function renderVolatility(vol) {
    const kws = vol.keywords || [];
    if (volChart) volChart.destroy();
    volChart = new Chart($('chart-volatility'), {
      type: 'bar',
      data: {
        labels: kws.map(k => k.keyword),
        datasets: [{
          label: 'Volatility',
          data: kws.map(k => k.score),
          backgroundColor: '#7030a0',
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        scales: { x: { max: 100, title: { display: true, text: 'Volatility score' } } },
        plugins: { legend: { display: false } },
      },
    });
  }

  // ── Section 6 — ads pressure dual line ──
  function renderAds(ads) {
    const section = $('ads-section'), empty = $('ads-empty');
    if (!ads.has_data) {
      empty.classList.remove('hidden');
      $('chart-ads').classList.add('hidden');
      if (adsChart) { adsChart.destroy(); adsChart = null; }
      return;
    }
    empty.classList.add('hidden');
    $('chart-ads').classList.remove('hidden');
    const dates = ads.series.map(s => s.run_date);
    if (adsChart) adsChart.destroy();
    adsChart = new Chart($('chart-ads'), {
      type: 'line',
      data: {
        labels: dates,
        datasets: [
          { label: 'Ads detected', data: ads.series.map(s => s.total_ads), borderColor: '#1f3864', backgroundColor: '#1f386422', tension: 0.2, fill: false },
          { label: 'Offshore ads', data: ads.series.map(s => s.offshore_ads), borderColor: '#c00000', backgroundColor: '#c0000022', borderDash: [5, 4], tension: 0.2, fill: false },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, title: { display: true, text: 'Ads per run' } } },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  $('range-select').addEventListener('change', load);
  $('keyword-select').addEventListener('change', load);
  load();
})();
