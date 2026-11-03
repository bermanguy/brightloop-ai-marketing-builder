import React, { useEffect, useId, useState } from 'react';
import { AlertTriangle, ArrowUpRight, Check, ChevronDown, EyeOff, ExternalLink, History, Undo2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { hostLabel, withProtocol } from '@/lib/links';
import { isExpanded, setExpanded } from '@/lib/expanded';
import { OPEN_EVENT, requestLatest } from '@/lib/goToLatest';
import { setHidden, useHiddenIds } from '@/lib/hidden';
import Markup from '@/components/Markup';
import Collapse from '@/components/Collapse';
import CopyButton from '@/components/CopyButton';
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
// Short names for the change type. The engine's own labels stay in the API.
const CHANGE_TYPE = {
  pricing: 'Pricing',
  packaging: 'Packaging',
  signup_funnel: 'Signup Funnel',
  pricing_page_ui: 'Pricing Page UI',
  other: 'Other',
};
// What the source confidence score (set by rule from where the quote came from) means, by source kind.
const SOURCE_KIND = {
  own_pricing_page: 'official competitor pricing page',
  own_site_other_page: "another page on the competitor's own site",
  third_party: 'third-party source',
  sponsored_or_anonymous: 'sponsored or anonymous source',
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

function SourceBlock({ source, unverified }) {
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
          <span className="truncate">{withProtocol(source.url)}</span>
          {unverified ? null : <span className="sr-only"> (official source)</span>}
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

// The evidence, one click away: the exact quote with Copy quote, its link, and the history across checks.
function Evidence({ item, unverified, observation }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 transition-colors hover:text-indigo-600"
      >
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform duration-200', open && 'rotate-180')} />
        {open ? 'Hide evidence' : 'View evidence'}
      </button>
      <Collapse open={open}>
        <div id={panelId} className="mt-2 space-y-3">
          <Section label={unverified ? "What's claimed" : 'What the page shows'}>
            <div className="space-y-2">
              {item.sources.map((s, index) => (
                <SourceBlock key={`${s.url}-${index}`} source={s} unverified={unverified} />
              ))}
            </div>
          </Section>
          {observation ? (
            <Section label="History across checks" icon={History}>
              <p className="text-sm leading-relaxed text-slate-700">{observation}</p>
            </Section>
          ) : null}
        </div>
      </Collapse>
    </div>
  );
}

export default function ChangeCard({ item, isNew }) {
  const unverified = Boolean(item.unverified);
  const interpretation = !unverified && item.interpretation ? item.interpretation : null;
  // An older card a later check superseded. Cards with their own status say so in it; the rest get a tag.
  const superseded = Boolean(item.latest_item_id);
  const legacySuperseded = superseded && !interpretation;
  // Next steps: the checked interpretation's, else the engine's change-specific rules (D43), else the card's own.
  const steps = legacySuperseded
    ? []
    : interpretation
    ? (interpretation.actions || []).map((action) => action.text)
    : item.display_steps?.length
      ? item.display_steps
      : item.steps?.length
        ? item.steps
        : item.action
          ? [item.action]
          : [];
  const summary = interpretation
    ? interpretation.status_detail
    : legacySuperseded
      ? 'A later check changed this again, so this card is history.'
      : steps[0];
  const changeType = CHANGE_TYPE[item.category] || item.category_label;
  // A status is shown only while it still holds: once a later check changed the same line, the card is history.
  const statusLabel = superseded && interpretation?.status !== 'changed_again' ? null : interpretation?.status_label;
  const source = item.sources?.[0];
  const impact = interpretation?.impact;
  const hidden = useHiddenIds().has(item.id);
  const [open, setOpen] = useState(() => isExpanded(item.id));
  const panelId = useId();

  useEffect(() => {
    const onOpen = (event) => {
      if (event.detail === item.id) {
        setOpen(true);
        setExpanded(item.id, true);
      }
    };
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_EVENT, onOpen);
  }, [item.id]);

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
        'rounded-xl border p-4 transition-shadow duration-200 sm:p-5',
        hidden ? 'border-dashed border-slate-300' : 'border-slate-200',
        unverified || hidden ? 'bg-slate-50/80 shadow-none hover:shadow-sm' : 'bg-white shadow-sm hover:shadow-md'
      )}
    >
      {/* Who, when, and whether the source is verified. */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <CompetitorAvatar competitor={item.competitor} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span className={cn('truncate text-sm font-medium', unverified ? 'text-slate-600' : 'text-slate-900')}>
                {item.competitor}
              </span>
              {superseded ? (
                <span className="inline-flex shrink-0 items-center rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">
                  Earlier change
                </span>
              ) : null}
              {hidden ? (
                <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">
                  <EyeOff className="h-3 w-3" />
                  Hidden
                </span>
              ) : null}
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
        <div className="shrink-0">
          <SourceBadge item={item} />
        </div>
      </div>

      {/* The kind of change, and the status only where the checked interpretation supports one. */}
      {changeType || statusLabel ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {changeType ? <Chip className="border-slate-200 bg-slate-50 text-slate-600">{changeType}</Chip> : null}
          {statusLabel ? (
            <Chip className={STATUS_STYLE[interpretation.status] || STATUS_STYLE.page_change_only}>{statusLabel}</Chip>
          ) : null}
        </div>
      ) : null}

      <h3
        className={cn(
          'mt-2 break-words text-base font-semibold leading-snug',
          unverified ? 'text-slate-700' : 'text-slate-900'
        )}
      >
        <Markup text={item.display_headline || item.headline} />
      </h3>

      {/* The one-line summary is repeated in full below, so it's shown only while collapsed. */}
      {summary && !open ? (
        <p className="mt-1.5 line-clamp-2 break-words text-sm leading-relaxed text-slate-600">
          <Markup text={summary} />
        </p>
      ) : null}

      {/* Expanded: what's uncertain, what to do next, then the source, with the quote one click away. */}
      <Collapse open={open}>
        <div id={panelId} className="mt-4 space-y-4 border-t border-slate-100 pt-4">
          {interpretation?.status_detail ? (
            <Section label={interpretation.question ? "What we don't know yet" : 'What it means'}>
              <p className="text-sm leading-relaxed text-slate-700">{interpretation.status_detail}</p>
            </Section>
          ) : null}

          {legacySuperseded ? (
            <Section label="What it means">
              <p className="text-sm leading-relaxed text-slate-700">
                A later check changed this again, so this card is history. Nothing to do here.
              </p>
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
          ) : null}

          {source ? (
            <div className="space-y-2">
              <div className="flex flex-col gap-1 text-xs leading-relaxed text-slate-500">
                {item.confidence != null ? (
                  <p>
                    Source confidence: {item.confidence}
                    {SOURCE_KIND[item.source_kind] ? ` — ${SOURCE_KIND[item.source_kind]}` : ''}. This reflects source
                    type, not certainty about business impact.
                  </p>
                ) : null}
                <a
                  href={withProtocol(source.url)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex min-w-0 items-center gap-1.5 font-medium text-indigo-600 hover:text-indigo-700 hover:underline"
                >
                  <ExternalLink className="h-3 w-3 shrink-0" />
                  <span className="truncate">
                    {unverified ? 'Source' : 'Official source'} · {hostLabel(source.url)}
                  </span>
                </a>
              </div>
              <Evidence item={item} unverified={unverified} observation={interpretation?.observation?.text} />
            </div>
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
        <div className="flex shrink-0 items-center gap-4">
          {superseded ? (
            <button
              type="button"
              onClick={() => requestLatest(item.latest_item_id)}
              className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 transition-colors hover:text-indigo-600"
            >
              Go to latest
              <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => setHidden(item.id, !hidden)}
            title={hidden ? 'Show this card in Focused view again' : 'Leave this card out of Focused view (it stays in All changes)'}
            className="inline-flex items-center gap-1 text-xs text-slate-400 transition-colors hover:text-slate-700"
          >
            {hidden ? <Undo2 className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
            {hidden ? 'Unhide' : 'Hide'}
          </button>
        </div>
      </div>
    </article>
  );
}
