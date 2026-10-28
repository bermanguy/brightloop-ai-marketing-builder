export function withProtocol(url) {
  if (!url) return '';
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

export function hostLabel(url) {
  const value = String(url || '').replace(/^https?:\/\//i, '').replace(/\/+$/, '');
  return value || String(url || '');
}