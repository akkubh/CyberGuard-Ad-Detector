/**
 * CyberGuard – popup.js
 * ─────────────────────────────────────────────────────────────────────────────
 * TECHNICAL EXPLANATION:
 * This script runs inside the popup.html context. It has access to the
 * Chrome Extension APIs but NOT the web page's DOM (that's content.js's job).
 *
 * Flow:
 *  1. On open: reads cached scan result from chrome.storage.local (put there
 *     by background.js after the last scan) and renders the UI.
 *  2. "Scan Now": sends FORCE_SCAN to content.js → content.js calls
 *     background.js → FastAPI → result returned and displayed.
 *  3. Report: builds a structured JSON payload and sends it via background.js
 *     to the FastAPI /report endpoint (simulated if offline).
 * ─────────────────────────────────────────────────────────────────────────────
 */

'use strict';

// ── DOM REFS ──────────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);

const gaugeCard     = $('gaugeCard');
const gaugeLoader   = $('gaugeLoader');
const gaugeFill     = $('gaugeFill');
const gaugeScoreText= $('gaugeScoreText');
const scoreBig      = $('scoreBig');
const verdictBadge  = $('verdictBadge');
const categoryText  = $('categoryText');
const categoryTag   = $('categoryTag');
const riskBarFill   = $('riskBarFill');
const keywordsWrap  = $('keywordsWrap');
const pageUrl       = $('pageUrl');
const statusDot     = $('statusDot');
const offlineBanner = $('offlineBanner');
const btnScan       = $('btnScan');
const btnReport     = $('btnReport');
const reportToggle  = $('reportToggle');
const reportBody    = $('reportBody');
const reportChevron = $('reportChevron');
const metaRisk      = $('metaRisk');
const metaType      = $('metaType');
const metaTime      = $('metaTime');
const metaKwCount   = $('metaKwCount');
const reporterName  = $('reporterName');
const reportComment = $('reportComment');
const toast         = $('toast');

// ── GAUGE ARC MATH ────────────────────────────────────────────────────────────
// The SVG arc path has a half-circumference of ~148 units (π × r ≈ 3.14 × 47)
const HALF_CIRC = 147.65;

function setGauge(score) {
  const filled = (score / 100) * HALF_CIRC;
  gaugeFill.setAttribute('stroke-dasharray', `${filled.toFixed(1)} ${HALF_CIRC}`);
}

// ── COLOUR LOOKUP ─────────────────────────────────────────────────────────────
function getRiskStyle(score) {
  if (score <= 30) return { color: '#00ff9d', cls: 'risk-safe',     accent: '#00c8ff' };
  if (score <= 60) return { color: '#ffb800', cls: 'risk-caution',  accent: '#ffb800' };
  if (score <= 80) return { color: '#ff6b35', cls: 'risk-high',     accent: '#ff6b35' };
  return              { color: '#ff2d55', cls: 'risk-critical', accent: '#ff2d55' };
}

// ── RENDER RESULT ─────────────────────────────────────────────────────────────
function renderResult(result) {
  if (!result) return;

  const score   = result.risk_score ?? 0;
  const style   = getRiskStyle(score);
  const isFake  = score > 40;
  const kwMap   = result.flagged_keywords ?? {};
  const totalKw = Object.values(kwMap).reduce((n, arr) => n + arr.length, 0);

  // Gauge arc + colours
  setGauge(score);
  gaugeFill.setAttribute('stroke', style.color);
  gaugeScoreText.textContent = `${score}`;
  gaugeScoreText.setAttribute('fill', style.color);
  scoreBig.textContent   = `${score}`;
  scoreBig.style.color   = style.color;

  // Risk class on card
  gaugeCard.className = `gauge-card ${style.cls}`;
  gaugeCard.style.setProperty('--accent', style.accent);

  // Bar
  riskBarFill.style.width      = `${score}%`;
  riskBarFill.style.background = style.color;

  // Verdict badge
  if (result.offline) {
    verdictBadge.textContent  = 'BACKEND OFFLINE';
    verdictBadge.className    = 'verdict-badge verdict-unknown';
  } else if (isFake) {
    verdictBadge.textContent  = '🚨 FAKE / FRAUDULENT';
    verdictBadge.className    = 'verdict-badge verdict-fake';
  } else {
    verdictBadge.textContent  = '✅ APPEARS GENUINE';
    verdictBadge.className    = 'verdict-badge verdict-genuine';
  }

  // Category
  const cat = result.fraud_category ?? 'Unknown';
  categoryText.textContent = cat;

  // Keywords
  renderKeywords(kwMap);

  // Offline banner
  offlineBanner.classList.toggle('show', !!result.offline);
  statusDot.classList.toggle('offline', !!result.offline);

  // Populate report metadata
  metaRisk.textContent    = `${score}%`;
  metaType.textContent    = cat.split('/')[0].trim();
  metaTime.textContent    = result.scanned_at
    ? new Date(result.scanned_at).toLocaleTimeString()
    : '—';
  metaKwCount.textContent = `${totalKw} phrases`;

  // Enable report button only when there's a real result
  btnReport.disabled = result.offline || score === 0;
}

function renderKeywords(kwMap) {
  const total = Object.values(kwMap).reduce((n, arr) => n + arr.length, 0);

  if (total === 0) {
    keywordsWrap.innerHTML = '<p class="no-keywords">✅ No high-risk keywords detected.</p>';
    return;
  }

  keywordsWrap.innerHTML = Object.entries(kwMap)
    .filter(([, kws]) => kws.length > 0)
    .map(([cat, kws]) => `
      <div class="kw-category">
        <span class="kw-cat-label">${cat}</span>
        <div class="kw-tags">
          ${kws.map(k => `<span class="kw-tag">${k}</span>`).join('')}
        </div>
      </div>
    `).join('');
}

// ── LOADING STATE ─────────────────────────────────────────────────────────────
function setLoading(active) {
  gaugeLoader.classList.toggle('active', active);
  btnScan.disabled = active;
  if (active) {
    btnScan.innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px"></span> Scanning…';
  } else {
    btnScan.innerHTML = '<span>🔍</span> Scan This Page Now';
  }
}

// ── TOAST ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  toast.textContent  = msg;
  toast.className    = `toast ${type} show`;
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// ── REPORT TOGGLE ─────────────────────────────────────────────────────────────
reportToggle.addEventListener('click', () => {
  const open = reportBody.classList.toggle('open');
  reportChevron.classList.toggle('open', open);
});

// ── SCAN BUTTON ───────────────────────────────────────────────────────────────
btnScan.addEventListener('click', async () => {
  setLoading(true);

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) { setLoading(false); return; }

  chrome.tabs.sendMessage(tab.id, { type: 'FORCE_SCAN' }, () => {
    if (chrome.runtime.lastError) {
      // Content script not injected (e.g. chrome:// page)
      showToast('⚠️ Cannot scan this page type.', 'error');
      setLoading(false);
      return;
    }

    // Poll storage for the result (content.js → background.js → storage)
    let attempts = 0;
    const poll = setInterval(() => {
      attempts++;
      chrome.storage.local.get('lastScanResult', ({ lastScanResult }) => {
        if (lastScanResult || attempts > 20) {
          clearInterval(poll);
          setLoading(false);
          if (lastScanResult) renderResult(lastScanResult);
          else showToast('⚠️ Scan timed out. Is the backend running?', 'error');
        }
      });
    }, 400);
  });
});

// ── REPORT SUBMISSION ─────────────────────────────────────────────────────────
btnReport.addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.storage.local.get('lastScanResult', ({ lastScanResult }) => {
    if (!lastScanResult) {
      showToast('No scan result to report.', 'error');
      return;
    }

    const report = {
      report_type:      'CHROME_EXTENSION',
      timestamp:        new Date().toISOString(),
      reporter_name:    reporterName.value.trim() || 'Anonymous',
      comment:          reportComment.value.trim(),
      url:              lastScanResult.url,
      page_title:       lastScanResult.title ?? tab?.title ?? '',
      risk_score:       lastScanResult.risk_score,
      verdict:          lastScanResult.risk_score > 40 ? 'FAKE' : 'GENUINE',
      fraud_category:   lastScanResult.fraud_category,
      flagged_keywords: lastScanResult.flagged_keywords,
      evidence_text:    lastScanResult.text_snippet ?? '',
      tab_id:           tab?.id ?? null,
    };

    btnReport.disabled  = true;
    btnReport.innerHTML = '<span class="spinner" style="width:13px;height:13px;border-width:2px"></span> Submitting…';

    chrome.runtime.sendMessage({ type: 'SUBMIT_REPORT', report }, (resp) => {
      btnReport.disabled  = false;
      btnReport.innerHTML = '<span>📡</span> Submit Report to Database';

      if (resp?.ok) {
        const id  = resp.data?.report_id ?? 'N/A';
        const sim = resp.simulated ? ' (Demo Mode)' : '';
        showToast(`✅ Report filed! ID: ${id}${sim}`, 'success');
        reportComment.value = '';
        reportBody.classList.remove('open');
        reportChevron.classList.remove('open');
      } else {
        showToast('❌ Report submission failed.', 'error');
      }
    });
  });
});

// ── INIT ──────────────────────────────────────────────────────────────────────
(async () => {
  // Show current tab URL
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.url) {
    try {
      pageUrl.textContent = new URL(tab.url).hostname + new URL(tab.url).pathname.slice(0, 30);
    } catch {
      pageUrl.textContent = tab.url.slice(0, 50);
    }
  }

  // Load cached scan result
  chrome.storage.local.get('lastScanResult', ({ lastScanResult }) => {
    if (lastScanResult) {
      renderResult(lastScanResult);
    } else {
      // No result yet — show idle state
      verdictBadge.textContent = 'NOT SCANNED';
      verdictBadge.className   = 'verdict-badge verdict-unknown';
    }
  });
})();
