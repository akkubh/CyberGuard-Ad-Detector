/**
 * CyberGuard – content.js
 * ─────────────────────────────────────────────────────────────────────────────
 * TECHNICAL EXPLANATION:
 * This Content Script runs in the context of every web page the user visits.
 * It has direct access to the page's DOM but runs in an isolated world
 * (cannot access page JS variables). It performs three jobs:
 *
 *  1. TRIGGER DETECTION: Scans visible text for Indian scam keywords using a
 *     fast regex pass. If ≥3 triggers are found, it requests an AI scan.
 *
 *  2. TEXT EXTRACTION: Pulls clean visible text from the DOM, stripping
 *     scripts, styles, and nav elements to reduce noise for the ML model.
 *
 *  3. FLOATING BADGE: Injects a non-intrusive floating pill into the page
 *     showing the risk level. Clicking it opens the extension popup.
 *
 * Communication: Uses chrome.runtime.sendMessage() to talk to background.js
 * (the service worker) which relays the text to the FastAPI backend.
 * ─────────────────────────────────────────────────────────────────────────────
 */

'use strict';

// ── CONFIG ───────────────────────────────────────────────────────────────────

// Minimum trigger keyword hits before we fire an AI scan request
const TRIGGER_THRESHOLD = 2;

// Scam-domain trigger keywords (fast pre-filter before calling the API)
const TRIGGER_KEYWORDS = [
  // Job scam signals
  'work from home', 'earn daily', 'earn weekly', 'immediate joining',
  'no experience needed', 'no qualification', 'registration fee',
  'data entry job', 'part time job', 'daily payment',
  // Loan scam signals
  'instant loan', 'no cibil', 'no documents required', 'guaranteed approval',
  'aadhar loan', 'bad cibil', 'no income proof', 'processing advance',
  // Investment scam signals
  'guaranteed returns', '100% profit', 'double money', 'crypto trading',
  'mlm opportunity', 'passive income', 'invest and earn',
  // Universal pressure
  'limited time offer', 'apply now urgently', 'whatsapp now',
  'join our group', '100% guaranteed',
];

// ── STATE ────────────────────────────────────────────────────────────────────
let badgeEl        = null;   // The floating DOM badge element
let lastScanResult = null;   // Most recent API result (shared with popup)
let scanDebounce   = null;   // Debounce timer for DOM mutation observer

// ── 1. TRIGGER DETECTION ─────────────────────────────────────────────────────
/**
 * Quick pre-scan: count how many trigger keywords appear in visible page text.
 * Returns the hit count. We avoid calling the API on every page – only pages
 * that already look suspicious.
 */
function countTriggerHits(text) {
  const lower = text.toLowerCase();
  return TRIGGER_KEYWORDS.filter(kw => lower.includes(kw)).length;
}

// ── 2. TEXT EXTRACTION ───────────────────────────────────────────────────────
/**
 * Extracts clean, useful visible text from the DOM.
 * We skip <script>, <style>, <nav>, <header>, <footer> to reduce noise.
 * Ad text usually appears in <p>, <div>, <span>, <article>, <section>.
 */
function extractPageText() {
  const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'HEADER',
                              'FOOTER', 'ASIDE', 'IFRAME', 'SVG', 'CANVAS']);
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        let el = node.parentElement;
        while (el) {
          if (SKIP_TAGS.has(el.tagName)) return NodeFilter.FILTER_REJECT;
          el = el.parentElement;
        }
        return node.textContent.trim().length > 3
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_SKIP;
      }
    }
  );

  const chunks = [];
  let node;
  while ((node = walker.nextNode())) {
    chunks.push(node.textContent.trim());
  }

  // Limit to 3000 chars to keep API payload light
  return chunks.join(' ').replace(/\s+/g, ' ').slice(0, 3000);
}

// ── 3. FLOATING BADGE ────────────────────────────────────────────────────────
/**
 * Injects (or updates) the floating CyberGuard badge at the bottom-right
 * of the page. The badge shows the risk level with colour coding.
 *
 * Risk level → colour mapping:
 *   SAFE      (0–30%)   → neon green  #00ff9d
 *   CAUTION   (31–60%)  → amber       #ffb800
 *   HIGH RISK (61–80%)  → orange      #ff6b35
 *   CRITICAL  (81–100%) → red         #ff2d55
 */
function getRiskColor(score) {
  if (score <= 30) return { color: '#00ff9d', label: 'SAFE',      icon: '🛡️' };
  if (score <= 60) return { color: '#ffb800', label: 'CAUTION',   icon: '⚠️' };
  if (score <= 80) return { color: '#ff6b35', label: 'HIGH RISK', icon: '🚨' };
  return              { color: '#ff2d55', label: 'CRITICAL',  icon: '🔴' };
}

function injectBadge(score, category) {
  // Remove existing badge if present
  if (badgeEl) badgeEl.remove();

  const { color, label, icon } = getRiskColor(score);

  badgeEl = document.createElement('div');
  badgeEl.id = 'cyberguard-badge';
  badgeEl.innerHTML = `
    <div class="cg-badge-inner">
      <span class="cg-icon">${icon}</span>
      <div class="cg-text">
        <span class="cg-title">CyberGuard</span>
        <span class="cg-label" style="color:${color}">${label} · ${score}%</span>
      </div>
      <div class="cg-bar-wrap">
        <div class="cg-bar-fill" style="width:${score}%;background:${color}"></div>
      </div>
    </div>
  `;

  // Click badge → focus the extension popup (best-effort; popups can't be
  // opened programmatically from content scripts, so we send a message to
  // background.js which shows a notification instead)
  badgeEl.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'OPEN_POPUP' });
  });

  document.body.appendChild(badgeEl);

  // Auto-hide after 8 seconds unless CRITICAL
  if (score <= 80) {
    setTimeout(() => {
      if (badgeEl) {
        badgeEl.style.transition = 'opacity 0.5s, transform 0.5s';
        badgeEl.style.opacity    = '0';
        badgeEl.style.transform  = 'translateX(120%)';
        setTimeout(() => badgeEl && badgeEl.remove(), 500);
      }
    }, 8000);
  }
}

// ── MAIN SCAN FLOW ────────────────────────────────────────────────────────────
/**
 * Full scan pipeline:
 *  1. Extract text from DOM
 *  2. Run quick trigger check (avoid API for obviously safe pages)
 *  3. Send to background.js → FastAPI backend
 *  4. Receive result, inject badge, cache result for popup
 */
async function runScan(triggeredByUser = false) {
  const pageText = extractPageText();
  if (!pageText || pageText.length < 30) return;

  const hits = countTriggerHits(pageText);

  // Only auto-scan if enough trigger keywords found, OR if user forced scan
  if (!triggeredByUser && hits < TRIGGER_THRESHOLD) return;

  // Send to background service worker
  chrome.runtime.sendMessage(
    {
      type:    'SCAN_TEXT',
      text:    pageText,
      url:     window.location.href,
      title:   document.title,
      hits:    hits,
    },
    (response) => {
      if (chrome.runtime.lastError || !response) return;
      lastScanResult = response;

      // Cache result in storage so popup can read it instantly
      chrome.storage.local.set({ lastScanResult: response });

      // Show floating badge if risky or user-triggered
      if (response.risk_score > 20 || triggeredByUser) {
        injectBadge(response.risk_score, response.fraud_category);
      }
    }
  );
}

// ── DOM MUTATION OBSERVER ─────────────────────────────────────────────────────
/**
 * Watch for dynamic content changes (SPAs, lazy-loaded ads).
 * Debounced to 1500ms to avoid hammering the API on every tiny DOM change.
 */
const observer = new MutationObserver(() => {
  clearTimeout(scanDebounce);
  scanDebounce = setTimeout(() => runScan(false), 1500);
});

// ── LISTEN FOR MESSAGES FROM POPUP ───────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'GET_SCAN_RESULT') {
    // Popup is asking for the latest result
    sendResponse(lastScanResult);
    return true;
  }
  if (msg.type === 'FORCE_SCAN') {
    // User clicked "Scan Now" in popup
    runScan(true);
    sendResponse({ ok: true });
    return true;
  }
  if (msg.type === 'GET_PAGE_INFO') {
    sendResponse({
      url:   window.location.href,
      title: document.title,
      text:  extractPageText().slice(0, 500),
    });
    return true;
  }
});

// ── INIT ─────────────────────────────────────────────────────────────────────
// Run initial scan after a short delay to let the page fully render
setTimeout(() => {
  runScan(false);
  observer.observe(document.body, { childList: true, subtree: true });
}, 1200);
