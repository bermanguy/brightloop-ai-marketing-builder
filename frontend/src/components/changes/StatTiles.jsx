import React from 'react';
import StatTile from '@/components/changes/StatTile';

export default function StatTiles({ summary, focus, competitor, onSelectFocus }) {
  const toggleFocus = (value) => onSelectFocus(focus === value ? '' : value);

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <StatTile
        label="All changes"
        value={summary?.total ?? 0}
        active={!focus && !competitor}
        onClick={() => onSelectFocus('')}
      />
      <StatTile
        label="Verified"
        value={summary?.verified ?? 0}
        active={focus === 'verified'}
        onClick={() => toggleFocus('verified')}
      />
      <StatTile
        label="Unverified rumors"
        value={summary?.unverified ?? 0}
        active={focus === 'unverified'}
        onClick={() => toggleFocus('unverified')}
      />
    </div>
  );
}
