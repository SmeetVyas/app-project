/**
 * API Sentinel — Interactive Request Builder Engine
 * Enables live testing of public APIs with pre-flight SSRF protection and visual inspectors.
 */

document.addEventListener('DOMContentLoaded', function () {
  const sendBtn = document.getElementById('rbSendBtn');
  const methodSelect = document.getElementById('rbMethod');
  const urlInput = document.getElementById('rbUrl');
  const bodyInput = document.getElementById('rbBody');
  const formatJsonBtn = document.getElementById('rbFormatJsonBtn');
  const saveEndpointBtn = document.getElementById('rbSaveEndpointBtn');

  // Response UI elements
  const respEmptyState = document.getElementById('respEmptyState');
  const respLoadingState = document.getElementById('respLoadingState');
  const respContainer = document.getElementById('respContainer');
  const respStatusBadge = document.getElementById('respStatusBadge');
  const respLatencyBadge = document.getElementById('respLatencyBadge');
  const respSizeBadge = document.getElementById('respSizeBadge');
  const respBodyViewer = document.getElementById('respBodyViewer');
  const respHeadersViewer = document.getElementById('respHeadersViewer');
  const copyRespBtn = document.getElementById('copyRespBtn');

  // CSRF token helper
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Format JSON button handler
  if (formatJsonBtn && bodyInput) {
    formatJsonBtn.addEventListener('click', function () {
      try {
        const raw = bodyInput.value.trim();
        if (!raw) return;
        const parsed = JSON.parse(raw);
        bodyInput.value = JSON.stringify(parsed, null, 2);
      } catch (err) {
        alert('Invalid JSON: ' + err.message);
      }
    });
  }

  // Row Management for Headers and Params
  window.addKeyValueRow = function (containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'key-value-row';
    row.style = 'display: flex; gap: 8px; margin-bottom: 8px; align-items: center;';
    row.innerHTML = `
      <input type="text" class="form-input row-key font-mono" placeholder="Key" style="flex: 1;" />
      <input type="text" class="form-input row-val font-mono" placeholder="Value" style="flex: 2;" />
      <button type="button" class="btn btn-secondary btn-sm" onclick="this.parentElement.remove()" title="Remove">✕</button>
    `;
    container.appendChild(row);
  };

  function collectKeyValues(containerId) {
    const container = document.getElementById(containerId);
    const result = {};
    if (!container) return result;
    const rows = container.querySelectorAll('.key-value-row');
    rows.forEach(r => {
      const k = r.querySelector('.row-key').value.trim();
      const v = r.querySelector('.row-val').value.trim();
      if (k) result[k] = v;
    });
    return result;
  }

  // Send Outbound Request
  if (sendBtn) {
    sendBtn.addEventListener('click', async function () {
      const url = (urlInput.value || '').trim();
      if (!url) {
        alert('Please enter a target URL.');
        urlInput.focus();
        return;
      }

      const method = methodSelect.value;
      const headers = collectKeyValues('headersContainer');
      const params = collectKeyValues('paramsContainer');
      const body = bodyInput ? bodyInput.value : '';

      // Update UI to loading
      respEmptyState.style.display = 'none';
      respContainer.style.display = 'none';
      respLoadingState.style.display = 'block';
      sendBtn.disabled = true;
      sendBtn.innerHTML = `
        <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10"></path>
        </svg> Sending...
      `;

      try {
        const csrftoken = getCookie('csrftoken') || '';
        const resp = await fetch('/endpoints/builder/send/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
          },
          body: JSON.stringify({
            url: url,
            method: method,
            headers: headers,
            params: params,
            body: body,
          })
        });

        const data = await resp.json();
        renderResponse(data);
      } catch (err) {
        renderResponse({
          error: 'Client Network Error: Failed to contact API Sentinel execution engine. (' + err.message + ')',
          status_code: null,
          elapsed_ms: 0,
          headers: {},
          body: '',
        });
      } finally {
        respLoadingState.style.display = 'none';
        sendBtn.disabled = false;
        sendBtn.innerHTML = `Send Request`;
      }
    });
  }

  function renderResponse(res) {
    respContainer.style.display = 'block';

    if (res.error) {
      respStatusBadge.className = 'badge-status badge-failed';
      respStatusBadge.textContent = 'ERROR / BLOCKED';
      respLatencyBadge.textContent = `${res.elapsed_ms || 0}ms`;
      respSizeBadge.textContent = '0 B';
      respBodyViewer.textContent = res.error;
      respHeadersViewer.textContent = JSON.stringify(res.headers || {}, null, 2);
      return;
    }

    const statusCode = res.status_code || 0;
    const isSuccess = statusCode >= 200 && statusCode < 400;
    respStatusBadge.className = isSuccess ? 'badge-status badge-passed' : 'badge-status badge-failed';
    respStatusBadge.textContent = `${statusCode} ${getStatusText(statusCode)}`;

    respLatencyBadge.textContent = `${res.elapsed_ms}ms`;
    respSizeBadge.textContent = formatBytes(res.size_bytes || 0);

    // Formatted Body
    if (res.is_json && res.parsed_json) {
      respBodyViewer.textContent = JSON.stringify(res.parsed_json, null, 2);
    } else {
      respBodyViewer.textContent = res.body || '(Empty Response Body)';
    }

    // Headers
    respHeadersViewer.textContent = JSON.stringify(res.headers || {}, null, 2);

    // Copy Response Handler
    if (copyRespBtn) {
      copyRespBtn.onclick = function () {
        window.copyToClipboard(respBodyViewer.textContent, copyRespBtn);
      };
    }
  }

  // Save as Endpoint Handler
  if (saveEndpointBtn) {
    saveEndpointBtn.addEventListener('click', function () {
      const url = encodeURIComponent(urlInput.value || '');
      const method = encodeURIComponent(methodSelect.value || 'GET');
      window.location.href = `/endpoints/new/?from_builder=1&url=${url}&method=${method}`;
    });
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function getStatusText(code) {
    const textMap = {
      200: 'OK', 201: 'Created', 204: 'No Content',
      301: 'Moved Permanently', 302: 'Found',
      400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed',
      500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable', 504: 'Gateway Timeout'
    };
    return textMap[code] || '';
  }

  // Initialize tabs in builder
  if (window.initTabs) {
    window.initTabs('.rb-tabs-container');
    window.initTabs('.resp-tabs-container');
  }
});
