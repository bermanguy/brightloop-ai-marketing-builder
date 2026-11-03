import React, { useEffect, useState } from 'react';
import { fetchChanges } from '@/api/pricewatch';
import { readPreviousVisit } from '@/lib/lastVisit';
import HowItWorks from '@/components/changes/HowItWorks';
import FilterBar from '@/components/changes/FilterBar';
import StatTiles from '@/components/changes/StatTiles';
import ActionTiles from '@/components/changes/ActionTiles';
import { actionGroup } from '@/lib/actionGroups';
import ChangeFeed from '@/components/changes/ChangeFeed';
import ChangesSkeleton from '@/components/changes/ChangesSkeleton';
import ErrorState from '@/components/ErrorState';

const RANGE_LABELS = {
  7: 'last 7 days',
  30: 'last 30 days',
  all: 'all time',
};

export default function Changes() {
  const [days, setDays] = useState('7');
  const [competitor, setCompetitor] = useState('');
  const [focus, setFocus] = useState('');
  const [view, setView] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [previousVisit] = useState(() => readPreviousVisit());

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchChanges({ days, competitor, focus })
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || 'The pricing engine could not be reached.');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [days, competitor, focus, reloadKey]);

  const summary = data?.summary;
  const items = data?.items || [];
  // With interpretations on, the counters are about what to do; without them, the original counters are shown.
  const interpreted = items.some((item) => item.interpretation);
  const shown = interpreted && view ? items.filter((item) => actionGroup(item) === view) : items;
  const companyLabel = competitor || 'all companies';
  const summaryLine = summary
    ? `${summary.total} ${summary.total === 1 ? 'change' : 'changes'} · ${
        RANGE_LABELS[days] || RANGE_LABELS['7']
      } · ${companyLabel}`
    : null;

  return (
    <div className="space-y-6">
      <HowItWorks />

      <div className="sticky top-3 z-20">
        <FilterBar
          days={days}
          onDaysChange={setDays}
          competitor={competitor}
          onCompetitorChange={setCompetitor}
          competitors={data?.competitors || []}
          failedPages={data?.failed_pages || []}
          summaryLine={summaryLine}
        />
      </div>

      {loading ? (
        <ChangesSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setReloadKey((key) => key + 1)} />
      ) : (
        <div className="space-y-6">
          {interpreted ? (
            <ActionTiles items={items} view={view} onSelectView={setView} />
          ) : (
            <StatTiles
              summary={data?.summary}
              focus={focus}
              competitor={competitor}
              onSelectFocus={setFocus}
              onSelectCompetitor={setCompetitor}
            />
          )}
          <ChangeFeed items={shown} previousVisit={previousVisit} />
        </div>
      )}
    </div>
  );
}