import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import Collapse from '@/components/Collapse';
import RelativeTime from '@/components/RelativeTime';
import RunDetails from '@/components/runs/RunDetails';
import CompetitorAvatar from '@/components/CompetitorAvatar';
import { competitorFromLabel } from '@/lib/competitors';

function PageChip({ page }) {
  const competitor = competitorFromLabel(page.label);

  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border border-slate-200 bg-slate-50 py-0.5 pl-1 pr-1.5 text-[11px] text-slate-600">
      {competitor ? <CompetitorAvatar competitor={competitor} size="sm" /> : null}
      <span
        className={cn('h-1.5 w-1.5 shrink-0 rounded-full', page.ok ? 'bg-emerald-500' : 'bg-rose-500')}
      />
      {page.label}
    </span>
  );
}

export default function RunRow({ run }) {
  const [open, setOpen] = useState(false);
  const pages = run.pages || [];
  const errors = run.errors || [];
  const everyPageRead = pages.every((page) => page.ok);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3.5 text-left"
      >
        <span
          className={cn(
            'h-2.5 w-2.5 shrink-0 rounded-full',
            everyPageRead ? 'bg-emerald-500' : 'bg-amber-400'
          )}
          title={everyPageRead ? 'Every page was read' : 'Some pages failed'}
        />

        <RelativeTime
          value={run.started_at}
          className="w-[86px] shrink-0 text-sm font-medium text-slate-700"
        />

        <span className="inline-flex shrink-0 items-center gap-1.5">
          <span className="text-[11px] text-slate-400">Started by</span>
          <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">
            {run.trigger || '—'}
          </span>
        </span>

        <span className="flex flex-wrap items-center gap-1.5">
          {pages.map((page, index) => (
            <PageChip key={`${page.label}-${index}`} page={page} />
          ))}
        </span>

        <span className="ml-auto flex items-center gap-4 text-xs text-slate-500">
          <span className="whitespace-nowrap">
            {run.changes} {run.changes === 1 ? 'change' : 'changes'}
          </span>
          <span className="whitespace-nowrap tabular-nums">
            ${Number(run.cost_usd).toFixed(2)}
          </span>
          <span className={cn('whitespace-nowrap', errors.length > 0 && 'font-medium text-rose-600')}>
            {errors.length} {errors.length === 1 ? 'error' : 'errors'}
          </span>
          <ChevronDown
            className={cn(
              'h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200',
              open && 'rotate-180'
            )}
          />
        </span>
      </button>

      <Collapse open={open}>
        <RunDetails details={run.details} />
      </Collapse>
    </div>
  );
}