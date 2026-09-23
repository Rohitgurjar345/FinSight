const BASE_URL = 'http://127.0.0.1:5000';

async function handleResponse(res) {
  const data = await res.json();
  if (!res.ok) {
    const err = new Error(data.error || 'Request failed');
    err.details = data;
    err.status = res.status;
    throw err;
  }
  return data;
}

export async function uploadFiles(fileList) {
  const formData = new FormData();
  for (const file of fileList) {
    formData.append('files', file);
  }
  const res = await fetch(`${BASE_URL}/api/upload`, { method: 'POST', body: formData });
  return handleResponse(res);
}

export async function getHealthScore(sessionId) {
  const res = await fetch(`${BASE_URL}/api/health-score?session_id=${encodeURIComponent(sessionId)}`);
  return handleResponse(res);
}

export async function getLoanPreassessment(sessionId, fields) {
  const res = await fetch(`${BASE_URL}/api/loan-preassessment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, ...fields }),
  });
  return handleResponse(res);
}

export async function askAssistant(sessionId, query) {
  const res = await fetch(`${BASE_URL}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, query }),
  });
  return handleResponse(res);
}

export async function pingApi() {
  const res = await fetch(`${BASE_URL}/api/health`);
  return handleResponse(res);
}
