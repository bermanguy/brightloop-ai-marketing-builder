import React from 'react';
import { Inbox } from 'lucide-react';
import { groupByDay } from '@/lib/time';
import { isNewSinceVisit } from '@/lib/lastVisit';
import ChangeCard from '@/components/changes/ChangeCard';
import EmptyState from '@/components/EmptyState';

export default function ChangeFeed({ items = [], previousVisit }) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={Inbox}
        title="No pricing changes for this filter."
        description="Try a longer time range."
      />
    );
  }

  const groups = groupByDay(items);

  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <section key={group.key} className="space-y-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {group.label}
          </h2>
          <div className="space-y-3">
            {group.items.map((item) => (
              <ChangeCard
                key={item.id}
                item={item}
                isNew={isNewSinceVisit(item.seen_at, previousVisit)}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}