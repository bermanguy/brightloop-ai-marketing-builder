const BASE_URL = 'https://pricewatch-mb2k.onrender.com';

const POLL_EVERY_MS = 20000;
const POLL_UNTIL_MS = 5 * 60 * 1000;

async function getJson(path) {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`The pricing engine answered with ${response.status}.`);
  }
  return response.json();
}

async function readBody(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

export function fetchChanges({ days, competitor, focus }) {
  const params = new URLSearchParams();
  params.set('days', days || '7');
  if (competitor) params.set('competitor', competitor);
  if (focus) params.set('focus', focus);
  return getJson(`/api/changes?${params.toString()}`);
}

export function fetchPricing(competitor) {
  const params = new URLSearchParams();
  if (competitor) params.set('competitor', competitor);
  const query = params.toString();
  return getJson(`/api/pricing${query ? `?${query}` : ''}`);
}

export function fetchRuns() {
  return getJson('/api/runs');
}

// Whether a run is going now: { running, started_at, trigger }.
export function fetchCheckStatus() {
  return getJson('/api/check');
}

export function newestStartedAt(runs) {
  const starts = (Array.isArray(runs) ? runs : []).map((run) => run.started_at).filter(Boolean);
  starts.sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
  return starts[0] || null;
}

export async function startCheck() {
  const response = await fetch(`${BASE_URL}/api/check`, { method: 'POST' });
  return { status: response.status, data: await readBody(response) };
}

// The alert settings on the server, read-only: which channels are set up and the filters.
export function fetchAlertSettings() {
  return getJson('/api/alerts');
}

// Change the live alert settings. changes: any of email_on, slack_on, on_schedule, on_check_now (true/false),
// min_confidence, competitors ([names]), add_email, remove_email (position). Returns the new settings.
export async function saveAlertSettings(changes) {
  const response = await fetch(`${BASE_URL}/api/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  });
  const data = await readBody(response);
  if (!response.ok) throw new Error(data.error || `The pricing engine answered with ${response.status}.`);
  return data;
}

// Every alert sent or held back, test alerts and settings changes, newest first.
export function fetchAlertLog() {
  return getJson('/api/alerts/log');
}

// alerts: { channels: ['email', 'slack'], minConfidence, competitors: [names], emailTo }, all optional.
export async function runTest(file, alerts = {}) {
  const body = new FormData();
  body.append('cases', file);
  (alerts.channels || []).forEach((channel) => body.append('notify', channel));
  if (alerts.channels?.length) {
    if (alerts.minConfidence) body.append('min_confidence', String(alerts.minConfidence));
    if (alerts.competitors?.length) body.append('competitors', alerts.competitors.join(','));
    if (alerts.emailTo) body.append('email_to', alerts.emailTo);
  }

  const response = await fetch(`${BASE_URL}/api/test`, { method: 'POST', body });
  const data = await readBody(response);

  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : null;
    throw new Error(detail || data.message || `The pricing engine answered with ${response.status}.`);
  }

  return data;
}

// Waits for a run newer than `baseline` to show up in /api/runs.
export async function waitForNewRun(baseline) {
  const deadline = Date.now() + POLL_UNTIL_MS;

  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, POLL_EVERY_MS));

    try {
      const newest = newestStartedAt(await fetchRuns());
      if (newest && (!baseline || new Date(newest).getTime() > new Date(baseline).getTime())) {
        return newest;
      }
    } catch {
      // A failed poll is not fatal, the next one may work.
    }
  }

  return null;
}