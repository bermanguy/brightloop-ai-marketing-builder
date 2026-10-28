import React, { useEffect, useState } from 'react';
import { History, Loader2 } from 'lucide-react';
import { fetchRuns, fetchCheckStatus } from '@/api/pricewatch';
import { relativeTime } from '@/lib/time';
import RunRow from '@/components/runs/RunRow';
import RunsSkeleton from '@/components/runs/RunsSkeleton';
import EmptyState from '@/components/EmptyState';
import ErrorState from '@/components/ErrorState';

const STATUS_EVERY_MS = 10000;

function InProgressRow({ current }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-indigo-200 bg-indigo-50/60 px-4 py-3">
      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
      <span className="font-medium text-slate-900">In progress</span>
      <span className="text-sm text-slate-500">
        Started {relativeTime(current.started_at)}
        {current.trigger ? ` · ${current.trigger}` : ''} · usually about 2 minutes
      </span>
    </div>
  );
}

export default function RunLog() {
  const [runs, setRuns] = useState(null);
  const [current, setCurrent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchRuns()
      .then((result) => {
        if (cancelled) return;
        setRuns(Array.isArray(result) ? result : []);
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
  }, [reloadKey]);

  // Ask the engine whether a run is going; when one finishes, reload the list.
  useEffect(() => {
    let cancelled = false;
    let wasRunning = false;
    const poll = async () => {
      try {
        const status = await fetchCheckStatus();
        if (cancelled) return;
        if (wasRunning && !status.running) setReloadKey((key) => key + 1);
        wasRunning = Boolean(status.running);
        setCurrent(status.running ? status : null);
      } catch {
        // A failed poll is not fatal, the next one may work.
      }
    };
    poll();
    const timer = setInterval(poll, STATUS_EVERY_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  if (loading && !runs) return <RunsSkeleton />;
  if (error) return <ErrorState message={error} onRetry={() => setReloadKey((key) => key + 1)} />;
  if ((!runs || runs.length === 0) && !current) {
    return (
      <EmptyState
        icon={History}
        title="No runs recorded yet."
        description="Once the engine has read the competitor pages, every run appears here."
      />
    );
  }

  return (
    <div className="space-y-3">
      {current && <InProgressRow current={current} />}
      {(runs || []).map((run, index) => (
        <RunRow key={`${run.started_at}-${index}`} run={run} />
      ))}
    </div>
  );
}