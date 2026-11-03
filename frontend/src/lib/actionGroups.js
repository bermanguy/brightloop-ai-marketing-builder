// Which action counter a card belongs to. Labels and grouping only: every status comes from the engine's rules.
// An older card that a later check superseded (latest_item_id) counts under "Other changes", so one line that
// came and went is one investigation, not several.
export const ACTION_GROUPS = [
  { key: 'investigate', label: 'Needs investigation', hint: 'changes with an open question' },
  { key: 'confirmed', label: 'Change confirmed', hint: 'offer changes the source supports' },
  { key: 'other', label: 'Other changes', hint: 'earlier, page-only or not yet read' },
];

export function actionGroup(item) {
  const status = item.unverified || item.latest_item_id ? null : item.interpretation?.status;
  if (status === 'needs_investigation') return 'investigate';
  if (status === 'change_confirmed') return 'confirmed';
  return 'other';
}

export function countGroups(items) {
  const counts = { investigate: 0, confirmed: 0, other: 0 };
  items.forEach((item) => {
    counts[actionGroup(item)] += 1;
  });
  return counts;
}
