import React, { useCallback, useEffect, useState } from 'react';
import { fetchChanges } from '@/api/pricewatch';
import { readPreviousVisit } from '@/lib/lastVisit';
import HowItWorks from '@/components/changes/HowItWorks';
import FilterBar from '@/components/changes/FilterBar';
import SummaryCounters from '@/components/changes/SummaryCounters';
import FeedViewSelector from '@/components/changes/FeedViewSelector';
import HiddenCards from '@/components/changes/HiddenCards';
import { useGoToLatest } from '@/lib/goToLatest';
import { readFeedView, saveFeedView, useHiddenIds } from '@/lib/hidden';
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
  const [feedView, setFeedViewState] = useState(() => readFeedView());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [previousVisit] = useState(() => readPreviousVisit());

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchChanges({ days, competitor })
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
  }, [days, competitor, reloadKey]);

  const summary = data?.summary;
  const items = data?.items || [];
  // Focused view leaves out the cards hidden in this browser; All changes shows every card.
  const hiddenIds = useHiddenIds();
  const hiddenItems = items.filter((item) => hiddenIds.has(item.id));
  const shown = feedView === 'focused' ? items.filter((item) => !hiddenIds.has(item.id)) : items;
  const setFeedView = useCallback((value) => {
    setFeedViewState(value);
    saveFeedView(value);
  }, []);
  const showAll = useCallback(() => setFeedView('all'), [setFeedView]);
  const { outsideFilter, dismiss } = useGoToLatest(items, shown, showAll);
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
          <SummaryCounters total={summary?.total} verified={summary?.verified} unverified={summary?.unverified} />
          <FeedViewSelector view={feedView} onChange={setFeedView} total={items.length} hiddenCount={hiddenItems.length} />
          {outsideFilter ? (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-700">
              <span>The latest card about this is outside the current date range.</span>
              {days !== '30' && days !== 'all' ? (
                <button type="button" onClick={() => setDays('30')} className="font-medium text-indigo-600 hover:underline">
                  Show last 30 days
                </button>
              ) : null}
              <button type="button" onClick={dismiss} className="text-slate-500 hover:underline">
                Dismiss
              </button>
            </div>
          ) : null}
          <ChangeFeed items={shown} previousVisit={previousVisit} />
          <HiddenCards items={hiddenItems} hiddenTotal={hiddenIds.size} />
        </div>
      )}
    </div>
  );
}