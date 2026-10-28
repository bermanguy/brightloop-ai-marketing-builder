const LOGOS = {
  lovable: 'https://media.base44.com/images/public/6ae0f809a722303b343dd412/2e5e5e1ca_lovable.png',
  bolt: 'https://media.base44.com/images/public/6ae0f809a722303b343dd412/49885b4b1_bolt.png',
  replit: 'https://media.base44.com/images/public/6ae0f809a722303b343dd412/c68683ec9_replit.png',
  v0: 'https://media.base44.com/images/public/6ae0f809a722303b343dd412/8fc97c103_v0.png',
};

const BRANDS = {
  lovable: { name: 'Lovable', initials: 'L', accentText: 'text-rose-600' },
  bolt: { name: 'Bolt', initials: 'B', accentText: 'text-amber-600' },
  replit: { name: 'Replit', initials: 'R', accentText: 'text-emerald-600' },
  v0: { name: 'v0', initials: 'v0', accentText: 'text-violet-600' },
};

const keyOf = (name) => String(name || '').trim().toLowerCase();

export function competitorStyle(name) {
  const key = keyOf(name);
  const brand = BRANDS[key];

  return {
    logo: LOGOS[key] || null,
    initials: brand ? brand.initials : String(name || '').trim().slice(0, 1).toUpperCase() || '?',
    accentText: brand ? brand.accentText : 'text-slate-600',
  };
}

// Run-log pages only carry a label such as "Lovable (Monthly)".
export function competitorFromLabel(label) {
  const text = keyOf(label);
  const key = Object.keys(BRANDS).find((name) => text.startsWith(name));
  return key ? BRANDS[key].name : '';
}