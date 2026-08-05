// Throwaway script to verify buildApiUrl() routing logic.
// We copy the function verbatim from admin.js to test it in isolation.

const API_BASE_URL = '/admin/api';
const PUBLIC_API_BASE_URL = '/api/v1/public';

function buildApiUrl(path) {
  const normalizedPath = String(path || '').trim().replace(/^\/+/, '');
  if (!normalizedPath) throw new Error('La ruta de la API es requerida.');
  if (/^https?:\/\//i.test(normalizedPath)) {
    throw new Error('Las rutas de la API deben ser relativas.');
  }
  if (normalizedPath === 'public' || normalizedPath.startsWith('public/') || normalizedPath.startsWith('public?')) {
    return PUBLIC_API_BASE_URL + '/' + normalizedPath.replace(/^public\/?/, '');
  }
  if (normalizedPath.startsWith('api/')) {
    return '/' + normalizedPath;
  }
  return API_BASE_URL + '/' + normalizedPath.replace(/^admin\//, '');
}

const cases = [
  ['admin/dashboard', '/admin/api/dashboard'],
  ['admin/auth/logout', '/admin/api/auth/logout'],
  ['admin/access/activity-logs?per_page=100', '/admin/api/access/activity-logs?per_page=100'],
  ['public/tribute-types', '/api/v1/public/tribute-types'],
  ['public/availability?tribute_type_id=3&days=45', '/api/v1/public/availability?tribute_type_id=3&days=45'],
  ['public/slots?date=2026-08-04', '/api/v1/public/slots?date=2026-08-04'],
  ['public/appointments', '/api/v1/public/appointments'],
];

let allOk = true;
for (const [input, expected] of cases) {
  const got = buildApiUrl(input);
  const ok = got === expected;
  if (!ok) allOk = false;
  console.log(ok ? 'PASS' : 'FAIL', input, '->', got, ok ? '' : `(expected ${expected})`);
}
console.log(allOk ? '\nALL PASS' : '\nFAILURES');
process.exit(allOk ? 0 : 1);