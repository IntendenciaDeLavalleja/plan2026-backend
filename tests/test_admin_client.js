const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

let fetchImpl;
const document = {
  body: { classList: { contains: () => false, remove: () => {}, toggle: () => {} } },
  addEventListener: () => {},
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
};
const window = {
  crypto: { randomUUID: () => 'test-request-id' },
  location: { pathname: '/admin/login', assign: () => {} },
  matchMedia: () => ({ matches: false, addEventListener: () => {} }),
  setTimeout,
  clearTimeout,
};
const context = {
  AbortController,
  DOMException,
  FormData,
  console: { error: () => {} },
  document,
  fetch: (...args) => fetchImpl(...args),
  setTimeout,
  window,
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('app/static/admin/admin.js', 'utf8'), context);

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    url: 'https://example.test/api/v1/admin/auth/login',
    headers: { get: (name) => name.toLowerCase() === 'content-type' ? 'application/json' : null },
    text: async () => JSON.stringify(body),
  };
}

async function expectReject(promise, code) {
  await assert.rejects(promise, (error) => error.code === code);
}

async function main() {
  let firstSignal;
  fetchImpl = (_url, config) => new Promise((_resolve, reject) => {
    firstSignal = config.signal;
    config.signal.addEventListener('abort', () => reject(config.signal.reason), { once: true });
  });
  await expectReject(window.AdminUI.request('admin/auth/login', { timeout: 5 }), 'request_timeout');
  assert.equal(firstSignal.aborted, true);

  let secondSignal;
  fetchImpl = (_url, config) => {
    secondSignal = config.signal;
    return Promise.resolve(jsonResponse({ ok: true, data: { accepted: true } }));
  };
  assert.equal((await window.AdminUI.request('admin/auth/login', { timeout: 50 })).accepted, true);
  assert.notEqual(firstSignal, secondSignal);
  assert.equal(secondSignal.aborted, false);

  const retrySignals = new Set();
  fetchImpl = (_url, config) => {
    retrySignals.add(config.signal);
    return Promise.resolve(jsonResponse({ ok: true, data: { accepted: true } }));
  };
  for (let attempt = 0; attempt < 30; attempt += 1) {
    assert.equal((await window.AdminUI.request('admin/auth/login', { timeout: 50 })).accepted, true);
  }
  assert.equal(retrySignals.size, 30);
  assert.equal([...retrySignals].some((signal) => signal.aborted), false);

  fetchImpl = (_url, config) => Promise.resolve({
    ok: true,
    status: 200,
    url: 'https://example.test/api/v1/admin/auth/login',
    headers: { get: () => 'application/json' },
    text: () => new Promise((_resolve, reject) => config.signal.addEventListener('abort', () => reject(config.signal.reason), { once: true })),
  });
  await expectReject(window.AdminUI.request('admin/auth/login', { timeout: 5 }), 'request_timeout');

  const external = new AbortController();
  fetchImpl = (_url, config) => new Promise((_resolve, reject) => {
    config.signal.addEventListener('abort', () => reject(config.signal.reason), { once: true });
    external.abort(new DOMException('Navigation', 'AbortError'));
  });
  await expectReject(window.AdminUI.request('admin/auth/login', { signal: external.signal, timeout: 50 }), 'request_aborted');

  fetchImpl = () => Promise.resolve(jsonResponse({ ok: false, error: { code: 'two_factor_delivery_failed', message: 'No se pudo enviar' } }, 503));
  await expectReject(window.AdminUI.request('admin/auth/login'), 'two_factor_delivery_failed');
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
