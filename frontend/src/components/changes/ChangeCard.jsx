import React, { useState } from 'react';
import { AlertTriangle, Check, ChevronDown, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { hostLabel, withProtocol } from '@/lib/links';
import Markup from '@/components/Markup';
import Collapse from '@/components/Collapse';
import CopyButton from '@/components/CopyButton';
import ConfidenceBar from '@/components/ConfidenceBar';
import CompetitorAvatar from '@/components/CompetitorAvatar';
import RelativeTime from '@/components/RelativeTime';

function SourceBlock({ source }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <blockquote className="border-l-2 border-indigo-200 px-3 py-2.5 text-sm leading-relaxed text-slate-700">
        <Markup text={source.quote} />
      </blockquote>
      <div className="flex items-center justify-between gap-2 border-t border-slate-100 bg-slate-50/60 px-2.5 py-1">
        <a
          href={withProtocol(source.url)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-w-0 items-center gap-1.5 text-xs font-medium text-indigo-600 transition-colors hover:text-indigo-700 hover:underline"
        >
          <ExternalLink className="h-3 w-3 shrink-0" />
          <span className="truncate">{hostLabel(source.url)}</span>
        </a>
        <CopyButton value={source.quote} />
      </div>
    </div>
  );
}

export default function ChangeCard({ item, isNew }) {
  const [open, setOpen] = useState(false);
  const unverified = Boolean(item.unverified);
  const steps = item.steps?.length ? item.steps : item.action ? [item.action] : [];

  return (
    <article
      className={cn(
        'rounded-xl border border-slate-200 p-4 transition-shadow duration-200 sm:p-5',
        unverified ? 'bg-slate-50/80 shadow-none hover:shadow-sm' : 'bg-white shadow-sm hover:shadow-md'
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <CompetitorAvatar competitor={item.competitor} />
          <div>
            <div className="flex items-center gap-2">
              <span className={cn('text-sm font-medium', unverified ? 'text-slate-600' : 'text-slate-900')}>
                {item.competitor}
              </span>
              {isNew ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-600">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                  New
                </span>
              ) : null}
            </div>
            <RelativeTime value={item.seen_at} className="text-xs text-slate-500" />
          </div>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          {unverified ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-700">
              <AlertTriangle className="h-3.5 w-3.5" />
              Unverified: don&apos;t act yet
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
              <Check className="h-3.5 w-3.5" />
              Verified
            </span>
          )}
          <ConfidenceBar value={item.confidence} />
        </div>
      </div>

      <h3
        className={cn(
          'mt-3 text-base font-semibold leading-snug',
          unverified ? 'text-slate-700' : 'text-slate-900'
        )}
      >
        <Markup text={item.headline} />
      </h3>

      {item.sources?.length ? (
        <div className="mt-3.5">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {unverified ? "What's claimed" : 'What changed'}
          </div>
          <div className="space-y-2">
            {item.sources.map((source, index) => (
              <SourceBlock key={`${source.url}-${index}`} source={source} />
            ))}
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 transition-colors hover:text-indigo-600"
      >
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform duration-200', open && 'rotate-180')} />
        Details
      </button>

      <Collapse open={open}>
        <div className="mt-3 space-y-4 border-t border-slate-100 pt-3.5">
          {item.why ? (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Why it matters
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-700">
                <Markup text={item.why} />
              </p>
            </div>
          ) : null}

          {steps.length > 0 ? (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Recommended next steps
              </div>
              <ul className="mt-1.5 space-y-2">
                {steps.map((step, index) => (
                  <li key={index} className="flex gap-2.5 text-sm leading-relaxed text-slate-700">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-300" />
                    <Markup text={step} />
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </Collapse>
    </article>
  );
}