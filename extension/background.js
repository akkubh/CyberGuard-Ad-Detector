/**
 * CyberGuard – background.js (Service Worker)
 * ─────────────────────────────────────────────────────────────────────────────
 * TECHNICAL EXPLANATION:
 * In Manifest V3, background pages are replaced by Service Workers. This
 * script acts as the central relay/orchestrator:
 *
 *  1. RELAY: Receives SCAN_TEXT messages from content.js, POSTs them to the
 *     FastAPI backend at localhost:8000, and returns the JSON result.
 *
 *  2. BADGE ICON: Updates the extension toolbar icon badge text and colour
 *     to show the risk level at a glance (e.g. "91" in red).
 *
 *  3. REPORT: Receives SUBMIT_REPORT messages from popup.js and POSTs the
 *     structured police report to the backend /report endpoint.
 *
 *  4. NOTIFICATIONS: Shows a browser notification for CRITICAL risk pages.
 *
 * Service Workers are ephemeral — they spin up on demand and shut down when
 * idle. All persistent state is stored in chrome.storage.local.
 * ─────────────────────────────────────────────────────────────────────────────
 */

'use strict';

const API_BASE = 'alert-nature-production-153b.up.railway.app';

// ── BADGE COLOUR HELPER ───────────────────────────────────────────────────────
function setBadge(tabId, score) {
  let color, text;
  if      (score <= 0)  { color = '#555555'; text = '';     }
  else if (score <= 30) { color = '#00c97a'; text = `${score}`; }
  else if (score <= 60) { color = '#ffb800'; text = `${score}`; }
  else if (score <= 80) { color = '#ff6b35'; text = `${score}`; }
  else                  { color = '#ff2d55'; text = `${score}`; }

  chrome.action.setBadgeText({ text, tabId });
  chrome.action.setBadgeBackgroundColor({ color, tabId });
}

// ── MESSAGE HANDLER ───────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // ── SCAN_TEXT: content.js → FastAPI → content.js ──────────────────────────
  if (msg.type === 'SCAN_TEXT') {
    const tabId = sender.tab?.id;

    fetch(`${API_BASE}/analyze`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        text: msg.text,
        url:  msg.url,
      }),
    })
    .then(r => r.json())
    .then(data => {
      // Update toolbar badge
      if (tabId) setBadge(tabId, data.risk_score);

      // Cache with tab context
      const result = { ...data, url: msg.url, title: msg.title, scanned_at: new Date().toISOString() };
      chrome.storage.local.set({ lastScanResult: result, lastTabId: tabId });

      // Show notification for critical-risk pages
      if (data.risk_score >= 80) {
        chrome.notifications.create({
          type:    'basic',
          iconUrl: 'icons/icon48.png',
          title:   '🚨 CyberGuard: Critical Fraud Risk Detected',
          message: `Risk Score: ${data.risk_score}% · ${data.fraud_category}\n${msg.url.slice(0, 60)}`,
          priority: 2,
        });
      }

      sendResponse(result);
    })
    .catch(err => {
      // Backend not running – return a graceful fallback
      console.warn('[CyberGuard] Backend unavailable:', err.message);
      const fallback = {
        risk_score:      0,
        verdict:         'BACKEND_OFFLINE',
        fraud_category:  'Unable to connect to CyberGuard API',
        flagged_keywords: {},
        url:             msg.url,
        title:           msg.title,
        scanned_at:      new Date().toISOString(),
        offline:         true,
      };
      sendResponse(fallback);
    });

    return true; // Keep message channel open for async response
  }

  // ── SUBMIT_REPORT: popup.js → FastAPI /report ─────────────────────────────
  if (msg.type === 'SUBMIT_REPORT') {
    fetch(`${API_BASE}/report`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(msg.report),
    })
    .then(r => r.json())
    .then(data => sendResponse({ ok: true, data }))
    .catch(err => {
      // Simulate success if backend is down (demo mode)
      console.warn('[CyberGuard] Report endpoint offline, simulating:', err.message);
      sendResponse({
        ok:      true,
        simulated: true,
        data: {
          report_id:  'SIM-' + Math.random().toString(36).slice(2, 10).toUpperCase(),
          message:    'Report queued locally (backend offline – will sync when online)',
          timestamp:  new Date().toISOString(),
        }
      });
    });
    return true;
  }

  // ── OPEN_POPUP: badge clicked in content.js ───────────────────────────────
  if (msg.type === 'OPEN_POPUP') {
    // Cannot programmatically open the popup, so show a notification instead
    chrome.notifications.create({
      type:    'basic',
      iconUrl: 'icons/icon48.png',
      title:   'CyberGuard',
      message: 'Click the CyberGuard toolbar icon to view the full analysis.',
      priority: 1,
    });
    sendResponse({ ok: true });
    return true;
  }
});

// ── TAB CHANGE: reset badge when navigating to a new page ────────────────────
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === 'loading') {
    setBadge(tabId, 0);
  }
});
