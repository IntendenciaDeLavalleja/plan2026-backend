(function () {
  'use strict';

  const shell = document.body;
  const toggle = document.querySelector('[data-nav-toggle]');
  const sidebar = document.getElementById('admin-sidebar');
  const closeButtons = document.querySelectorAll('[data-nav-close]');
  const mobileNavigation = window.matchMedia('(max-width: 960px)');

  function syncNavAccessibility() {
    if (!sidebar) return;
    sidebar.inert = mobileNavigation.matches && !shell.classList.contains('is-nav-open');
  }

  function closeNav() {
    shell.classList.remove('is-nav-open');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    syncNavAccessibility();
    if (toggle && mobileNavigation.matches) toggle.focus();
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      const open = !shell.classList.contains('is-nav-open');
      shell.classList.toggle('is-nav-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      syncNavAccessibility();
      if (open && sidebar) {
        const firstLink = sidebar.querySelector('a, button');
        if (firstLink) firstLink.focus();
      }
    });
  }
  closeButtons.forEach(function (button) { button.addEventListener('click', closeNav); });
  mobileNavigation.addEventListener('change', function () {
    if (!mobileNavigation.matches) shell.classList.remove('is-nav-open');
    syncNavAccessibility();
  });
  syncNavAccessibility();
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && shell.classList.contains('is-nav-open')) closeNav();
  });

  function errorMessage(json, fallback) {
    if (json && json.error && typeof json.error === 'object') return json.error.message || fallback;
    if (json && typeof json.message === 'string') return json.message;
    return fallback;
  }

  async function request(url, options) {
    const config = Object.assign({ credentials: 'same-origin' }, options || {});
    config.headers = Object.assign({ Accept: 'application/json' }, config.headers || {});
    if (config.body && !(config.body instanceof FormData)) {
      config.headers = Object.assign({ 'Content-Type': 'application/json' }, config.headers);
      if (typeof config.body !== 'string') config.body = JSON.stringify(config.body);
    }
    let response;
    try {
      response = await fetch(url, config);
    } catch (error) {
      console.error('Error de red en la API administrativa.', { url: url, message: error && error.message });
      const networkError = new Error('No se pudo conectar con el sistema. Revisá la conexión e intentá nuevamente.');
      networkError.code = 'network_error';
      throw networkError;
    }

    const contentType = response.headers.get('content-type') || '';
    const rawBody = await response.text();
    if (!contentType.includes('application/json')) {
      console.error('Respuesta no JSON recibida de la API administrativa.', {
        url: response.url,
        status: response.status,
        contentType: contentType,
        bodyPreview: rawBody.slice(0, 500)
      });
      const contentError = new Error('El servidor respondió ' + response.status + ' con contenido no JSON.');
      contentError.status = response.status;
      throw contentError;
    }

    let json;
    try {
      json = rawBody ? JSON.parse(rawBody) : null;
    } catch (error) {
      console.error('Respuesta JSON inválida de la API administrativa.', {
        url: response.url,
        status: response.status,
        bodyPreview: rawBody.slice(0, 500)
      });
      const parseError = new Error('El servidor devolvió una respuesta JSON inválida.');
      parseError.status = response.status;
      throw parseError;
    }
    if (!response.ok || !json.ok) {
      const apiError = new Error(errorMessage(json, 'No se pudo completar la operación.'));
      apiError.code = json && json.error && json.error.code ? json.error.code : 'request_error';
      apiError.status = response.status;
      apiError.fields = json && json.error ? json.error.errors : null;
      if ((response.status === 401 || response.status === 403) && window.location.pathname !== '/admin/login') {
        window.location.assign('/admin/login');
      }
      throw apiError;
    }
    return json.data;
  }

  function notify(text, kind, target) {
    const box = typeof target === 'string' ? document.getElementById(target) : (target || document.getElementById('global-notice'));
    if (!box) return;
    box.textContent = text;
    box.className = 'admin-alert' + (kind ? ' is-' + kind : '');
    box.hidden = false;
    box.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    box.setAttribute('aria-live', kind === 'error' ? 'assertive' : 'polite');
  }

  function clearNotice(target) {
    const box = typeof target === 'string' ? document.getElementById(target) : (target || document.getElementById('global-notice'));
    if (!box) return;
    box.hidden = true;
    box.textContent = '';
  }

  function setBusy(button, busy, label) {
    if (!button) return;
    if (busy) {
      const count = Number(button.dataset.busyCount || 0);
      if (count === 0) button.dataset.originalLabel = button.textContent;
      button.dataset.busyCount = String(count + 1);
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      if (label) button.textContent = label;
    } else {
      const count = Math.max(0, Number(button.dataset.busyCount || 1) - 1);
      if (count > 0) {
        button.dataset.busyCount = String(count);
        return;
      }
      button.disabled = false;
      button.removeAttribute('aria-busy');
      if (button.dataset.originalLabel) button.textContent = button.dataset.originalLabel;
      delete button.dataset.originalLabel;
      delete button.dataset.busyCount;
    }
  }

  function openDialog(dialog, trigger) {
    if (!dialog) return;
    dialog._adminTrigger = trigger || document.activeElement;
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    const focusTarget = dialog.querySelector('[autofocus], input:not([type="hidden"]), select, textarea, button');
    if (focusTarget) window.setTimeout(function () { focusTarget.focus(); }, 0);
  }

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === 'function') dialog.close();
    else {
      dialog.removeAttribute('open');
      restoreDialogFocus(dialog);
    }
  }

  function restoreDialogFocus(dialog) {
    const trigger = dialog._adminTrigger;
    dialog._adminTrigger = null;
    if (trigger && trigger.isConnected && typeof trigger.focus === 'function') trigger.focus();
  }

  document.querySelectorAll('[data-dialog-close]').forEach(function (button) {
    button.addEventListener('click', function () { closeDialog(button.closest('dialog')); });
  });
  document.querySelectorAll('dialog').forEach(function (dialog) {
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) closeDialog(dialog);
    });
    dialog.addEventListener('close', function () { restoreDialogFocus(dialog); });
  });

  function formatDate(value) {
    if (!value) return 'Sin fecha';
    const parts = String(value).split('-').map(Number);
    if (parts.length !== 3) return String(value);
    return new Intl.DateTimeFormat('es-UY', { day: '2-digit', month: 'short', year: 'numeric' })
      .format(new Date(parts[0], parts[1] - 1, parts[2]));
  }

  function formatDateLong(value) {
    if (!value) return 'Sin fecha';
    const parts = String(value).split('-').map(Number);
    if (parts.length !== 3) return String(value);
    return new Intl.DateTimeFormat('es-UY', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
      .format(new Date(parts[0], parts[1] - 1, parts[2]));
  }

  function statusLabel(value) {
    return {
      reserved: 'Reservado',
      confirmed: 'Confirmado',
      attended: 'Atendido',
      cancelled: 'Cancelado',
      no_show: 'No asistió'
    }[value] || value || 'Sin estado';
  }

  function statusClass(value) {
    return {
      reserved: 'admin-badge-warning',
      confirmed: 'admin-badge-info',
      attended: 'admin-badge-success',
      cancelled: 'admin-badge-danger',
      no_show: 'admin-badge-danger'
    }[value] || '';
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  window.AdminUI = {
    request: request,
    notify: notify,
    clearNotice: clearNotice,
    setBusy: setBusy,
    openDialog: openDialog,
    closeDialog: closeDialog,
    formatDate: formatDate,
    formatDateLong: formatDateLong,
    statusLabel: statusLabel,
    statusClass: statusClass,
    escapeHtml: escapeHtml
  };
}());
