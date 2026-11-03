import React, { useId, useState } from 'react';
import { AlertTriangle, Check, ChevronDown, ExternalLink, History, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { hostLabel, withProtocol } from '@/lib/links';
import { isExpanded, setExpanded } from '@/lib/expanded';
import Markup from '@/components/Markup';
import Collapse from '@/components/Collapse';
import CopyButton from '@/components/CopyButton';
import ConfidenceBar from '@/components/ConfidenceBar';
import CompetitorAvatar from '@/components/CompetitorAvatar';
import RelativeTime from '@/components/RelativeTime';

// Display names and colours for the engine's fields. Labels only: every status and text comes from the engine's rules.
const STATUS_STYLE = {
  needs_investigation: 'border-amber-200 bg-amber-50 text-amber-800',
  change_confirmed: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  page_change_only: 'border-slate-200 bg-slate-50 text-slate-600',
  no_action_needed: 'border-slate-200 bg-slate-50 text-slate-600',
  changed_again: 'border-slate-200 bg-slate-50 text-slate-600',
};
const IMPACT = {
  trial_starts: 'Trial starts',
  signup_conversion: 'Signup conversion',
  activation: 'Activation',
  paid_conversion: 'Paid conversion',
  competitive_positioning: 'Competitive positioning',
};

function SectionLabel({ children, icon: Icon }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
      {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
      {children}
    </div>
  );
}

function Section({ label, icon, children }) {
  return (
    <section>
      <SectionLabel icon={icon}>{label}</SectionLabel>
      <div className="mt-1.5">{children}</div>
    </section>
  );
}

function SourceBlock({ source }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <blockquote className="break-words border-l-2 border-indigo-200 px-3 py-2.5 text-sm leading-relaxed text-slate-700">
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
          <span className="truncate">
            <span className="hidden sm:inline">Official source · </span>
            {hostLabel(source.url)}
          </span>
        </a>
        <span className="shrink-0 whitespace-nowrap">
          <CopyButton value={source.quote} />
        </span>
      </div>
    </div>
  );
}

function Chip({ className, children, title }) {
  return (
    <span
      title={title}
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-4',
        className
      )}
    >
      {children}
    </span>
  );
}

function SourceBadge({ item }) {
  if (item.unverified) {
    return (
      <Chip className="border-amber-200 bg-amber-50 font-semibold text-amber-700">
        <AlertTriangle className="h-3.5 w-3.5" />
        Unverified: don&apos;t act yet
      </Chip>
    );
  }
  return (
    <Chip className="border-emerald-200 bg-emerald-50 font-semibold text-emerald-700" title="The quote below is on the competitor's own page">
      <Check className="h-3.5 w-3.5" />
      Source verified
    </Chip>
  );
}

export default function ChangeCard({ item, isNew }) {
  const unverified = Boolean(item.unverified);
  const interpretation = !unverified && item.interpretation ? item.interpretation : null;
  const steps = interpretation
    ? (interpretation.actions || []).map((action) => action.text)
    : item.steps?.length
      ? item.steps
      : item.action
        ? [item.action]
        : [];
  const summary = interpretation ? interpretation.status_detail : steps[0];
  const source = item.sources?.[0];
  const impact = interpretation?.impact;
  const [open, setOpen] = useState(() => isExpanded(item.id));
  const panelId = useId();

  const toggle = () => {
    setOpen((value) => {
      setExpanded(item.id, !value);
      return !value;
    });
  };

  return (
    <article
      data-card-id={item.id}
      className={cn(
        'rounded-xl border border-slate-200 p-4 transition-shadow duration-200 sm:p-5',
        unverified ? 'bg-slate-50/80 shadow-none hover:shadow-sm' : 'bg-white shadow-sm hover:shadow-md'
      )}
    >
      {/* Collapsed: who, when, what kind, how sure, what changed, and the one open point. */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <CompetitorAvatar competitor={item.competitor} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={cn('truncate text-sm font-medium', unverified ? 'text-slate-600' : 'text-slate-900')}>
                {item.competitor}
              </span>
              {isNew ? (
                <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-600">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                  New
                </span>
              ) : null}
            </div>
            <RelativeTime value={item.seen_at} className="text-xs text-slate-500" />
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <SourceBadge item={item} />
          <ConfidenceBar value={item.confidence} />
        </div>
      </div>

      {item.category_label || interpretation?.status_label ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {item.category_label ? (
            <Chip
              className="border-slate-200 bg-slate-50 text-slate-600"
              title={interpretation ? 'Category chosen by AI from five options, then checked by rules' : 'Category set by rules'}
            >
              {item.category_label}
              {interpretation?.category_source === 'ai' ? (
                <span className="inline-flex items-center gap-0.5 text-indigo-500">
                  <Sparkles className="h-3 w-3" />
                  AI
                </span>
              ) : null}
            </Chip>
          ) : null}
          {interpretation?.status_label ? (
            <Chip className={STATUS_STYLE[interpretation.status] || STATUS_STYLE.page_change_only}>
              {interpretation.status_label}
            </Chip>
          ) : null}
        </div>
      ) : null}

      <h3
        className={cn(
          'mt-2.5 break-words text-base font-semibold leading-snug',
          unverified ? 'text-slate-700' : 'text-slate-900'
        )}
      >
        <Markup text={item.headline} />
      </h3>

      {/* The one-line summary is repeated in full below, so it's shown only while collapsed. */}
      {summary && !open ? (
        <p className="mt-1.5 line-clamp-2 break-words text-sm leading-relaxed text-slate-600">
          <Markup text={summary} />
        </p>
      ) : null}

      {/* Expanded: evidence, history, what's unknown, what to do, and impact only when there is one. */}
      <Collapse open={open}>
        <div id={panelId} className="mt-4 space-y-4 border-t border-slate-100 pt-4">
          {item.sources?.length ? (
            <Section label={unverified ? "What's claimed" : 'What the page shows'}>
              <div className="space-y-2">
                {item.sources.map((s, index) => (
                  <SourceBlock key={`${s.url}-${index}`} source={s} />
                ))}
              </div>
            </Section>
          ) : null}

          {interpretation?.observation?.text ? (
            <Section label="History across checks" icon={History}>
              <p className="text-sm leading-relaxed text-slate-700">{interpretation.observation.text}</p>
            </Section>
          ) : null}

          {interpretation?.status_detail ? (
            <Section label={interpretation.question ? "What we don't know yet" : 'What it means'}>
              <p className="text-sm leading-relaxed text-slate-700">{interpretation.status_detail}</p>
            </Section>
          ) : null}

          {steps.length > 0 ? (
            <section className="rounded-lg border border-indigo-100 bg-indigo-50/50 px-3.5 py-3">
              <div className="text-xs font-semibold uppercase tracking-wider text-indigo-700">What to do next</div>
              <ol className="mt-2 space-y-2">
                {steps.map((step, index) => (
                  <li key={index} className="flex gap-2.5 text-sm leading-relaxed text-slate-800">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white text-[11px] font-semibold text-indigo-600 ring-1 ring-indigo-200">
                      {index + 1}
                    </span>
                    <span className="min-w-0 break-words">
                      <Markup text={step} />
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          {impact?.text ? (
            <Section label={`Potential impact${IMPACT[impact.area] ? ` · ${IMPACT[impact.area]}` : ''}`}>
              <p className="text-sm leading-relaxed text-slate-700">{impact.text}</p>
            </Section>
          ) : !interpretation && item.why ? (
            <Section label="Why it matters">
              <p className="text-sm leading-relaxed text-slate-700">
                <Markup text={item.why} />
              </p>
            </Section>
          ) : null}
        </div>
      </Collapse>

      <div className="mt-3 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          aria-controls={panelId}
          className="inline-flex items-center gap-1.5 rounded-md text-xs font-medium text-indigo-600 transition-colors hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
        >
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform duration-200', open && 'rotate-180')} />
          {open ? 'Collapse' : 'View analysis'}
        </button>
        {source?.url && !open ? (
          <a
            href={withProtocol(source.url)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-w-0 items-center gap-1 text-xs text-slate-500 transition-colors hover:text-indigo-600"
          >
            <ExternalLink className="h-3 w-3 shrink-0" />
            <span className="truncate">{hostLabel(source.url)}</span>
          </a>
        ) : null}
      </div>
    </article>
  );
}
