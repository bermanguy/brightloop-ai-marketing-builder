import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { fetchRuns, newestStartedAt, startCheck, waitForNewRun } from '@/api/pricewatch';
import { relativeFuture } from '@/lib/time';
import { toast } from '@/components/ui/use-toast';

export default function CheckNowButton() {
  const [pending, setPending] = useState(false);
  const [nextAllowedAt, setNextAllowedAt] = useState(null);
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!nextAllowedAt) return undefined;
    const id = setInterval(() => setTick((tick) => tick + 1), 60000);
    return () => clearInterval(id);
  }, [nextAllowedAt]);

  const check = async () => {
    if (pending || nextAllowedAt) return;
    setPending(true);

    try {
      const baseline = newestStartedAt(await fetchRuns());
      const { status, data } = await startCheck();

      if (data.message) toast({ title: data.message });
      if (status === 429) {
        setNextAllowedAt(data.next_allowed_at || null);
        return;
      }

      if (status === 202) {
        const finished = await waitForNewRun(baseline);
        if (finished) {
          toast({ title: 'Check finished' });
          window.location.reload();
          return;
        }
        toast({
          title: 'The check is taking longer than usual.',
          description: 'This page was not refreshed.',
        });
      }
    } catch (err) {
      toast({
        title: err.message || 'The pricing engine could not be reached.',
        variant: 'destructive',
      });
    } finally {
      setPending(false);
    }
  };

  const blocked = Boolean(nextAllowedAt);
  const hoverText = blocked
    ? `Next check possible ${nextAllowedAt ? relativeFuture(nextAllowedAt) : 'later'}`
    : undefined;

  return (
    <span title={hoverText} className="inline-flex">
      <button
        type="button"
        onClick={check}
        disabled={pending || blocked}
        className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
      >
        {pending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5" />
        )}
        Check now
      </button>
    </span>
  );
}