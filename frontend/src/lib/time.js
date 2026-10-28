import moment from 'moment';

const EXACT_FORMAT = 'ddd D MMM, HH:mm';

export function exactTime(value) {
  if (!value) return '';
  const m = moment(value);
  return m.isValid() ? m.format(EXACT_FORMAT) : '';
}

export function relativeTime(value) {
  if (!value) return '';
  const m = moment(value);
  if (!m.isValid()) return '';

  const now = moment();
  const seconds = now.diff(m, 'seconds');
  if (seconds < 60) return 'just now';

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = now.clone().startOf('day').diff(m.clone().startOf('day'), 'days');
  if (days <= 1) return 'yesterday';
  if (days < 7) return `${days}d ago`;
  return m.format('ddd D MMM');
}

export function relativeFuture(value) {
  if (!value) return '';
  const m = moment(value);
  if (!m.isValid()) return '';

  const seconds = m.diff(moment(), 'seconds');
  if (seconds <= 0) return 'now';

  const minutes = Math.ceil(seconds / 60);
  if (minutes < 60) return `in ${minutes}m`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `in ${hours}h`;

  return m.format('ddd D MMM');
}

export function dayLabel(value) {
  const m = moment(value);
  const days = moment().startOf('day').diff(m.clone().startOf('day'), 'days');
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return m.format('ddd D MMM');
}

export function groupByDay(items) {
  const groups = [];
  const seen = new Map();

  (items || []).forEach((item) => {
    const key = moment(item.seen_at).format('YYYY-MM-DD');
    if (!seen.has(key)) {
      const group = { key, label: dayLabel(item.seen_at), items: [] };
      seen.set(key, group);
      groups.push(group);
    }
    seen.get(key).items.push(item);
  });

  return groups;
}