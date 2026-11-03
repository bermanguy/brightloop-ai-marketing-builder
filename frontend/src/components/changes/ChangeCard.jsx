import React, { useState } from 'react';
import { AlertTriangle, Check, ChevronDown, ExternalLink, HelpCircle, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { hostLabel, withProtocol } from '@/lib/links';
import Markup from '@/components/Markup';
import Collapse from '@/components/Collapse';
import CopyButton from '@/components/CopyButton';
import ConfidenceBar from '@/components/ConfidenceBar';
import CompetitorAvatar from '@/components/CompetitorAvatar';
import RelativeTime from '@/components/RelativeTime';

// Display names for the engine's interpretation fields. Labels only: nothing is computed here.
const DIRECTION = {
  more_for_customer: 'More for customers',
  less_for_customer: 'Less for customers',
  presentation_only: 'Presentation only',
  unclear: 'Unclear',
};
const AMBIGUITY = {
  meaning_of_mark_unknown: "what the removed mark referred to isn't known",
  mixed_changes: 'it mixes several changes',
  partial_quote: 'the quote shows only part of the change',
  changed_back_and_forth: 'this line has come and gone across recent checks',
  other: "the evidence doesn't say what it means for customers",
};
const IMPACT = {
  trial_starts: 'Trial starts',
  signup_conversion: 'Signup conversion',
  activation: 'Activation',
  paid_conversion: 'Paid conversion',
  competitive_positioning: 'Competitive positioning',
  unknown: 'Unknown',
};

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

function SectionLabel({ children }) {
  return <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{children}</div>;
}

function CategoryChip({ item }) {
  if (!item.category_label) return null;
  const ai = item.interpretation?.category_source === 'ai';
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-600">
      {item.category_label}
      {ai ? (
        <span className="inline-flex items-center gap-0.5 text-indigo-500" title="Category chosen by AI from five options, then checked by rules">
          <Sparkles className="h-3 w-3" />
          AI
        </span>
      ) : null}
    </span>
  );
}

// The engine's structured reading of a verified change, with the actions its rules chose.
function Interpretation({ interpretation }) {
  const ambiguous = interpretation.interpretation_status === 'ambiguous';
  const hasValues = interpretation.old_value || interpretation.new_value;

  return (
    <div className="mt-4 space-y-4">
      {interpretation.observation?.text ? (
        <div>
          <SectionLabel>Verified observation · across checks</SectionLabel>
          <p className="mt-1.5 text-sm leading-relaxed text-slate-700">{interpretation.observation.text}</p>
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
          <SectionLabel>AI reading of the change</SectionLabel>
        </div>
        <dl className="mt-2 grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-sm text-slate-700">
          {hasValues ? (
            <>
              <dt className="text-slate-500">Line removed</dt>
              <dd>{interpretation.old_value ? <Markup text={`“${interpretation.old_value}”`} /> : 'none'}</dd>
              <dt className="text-slate-500">Line added</dt>
              <dd>{interpretation.new_value ? <Markup text={`“${interpretation.new_value}”`} /> : 'none'}</dd>
            </>
          ) : null}
          <dt className="text-slate-500">Direction</dt>
          <dd>{DIRECTION[interpretation.direction] || interpretation.direction}</dd>
          <dt className="text-slate-500">Meaning</dt>
          <dd>
            {ambiguous ? (
              <span className="inline-flex items-start gap-1 text-amber-700">
                <HelpCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  Ambiguous: {AMBIGUITY[interpretation.ambiguity_reason] || AMBIGUITY.other}. The source is verified;
                  what it means isn&apos;t.
                </span>
              </span>
            ) : (
              'Supported by the verified source'
            )}
          </dd>
          <dt className="text-slate-500">Possible impact area</dt>
          <dd>
            {IMPACT[interpretation.potential_impact_area] || interpretation.potential_impact_area}
            <span className="text-slate-400"> · a possible area, not a prediction</span>
          </dd>
        </dl>
      </div>

      <div>
        <SectionLabel>What to do next</SectionLabel>
        {ambiguous ? (
          <p className="mt-1 text-xs text-slate-500">The meaning isn&apos;t clear yet, so only checks are suggested.</p>
        ) : null}
        <ul className="mt-1.5 space-y-2">
          {(interpretation.actions || []).map((action) => (
            <li key={action.id} className="flex gap-2.5 text-sm leading-relaxed text-slate-800">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
              <span>{action.text}</span>
            </li>
          ))}
        </ul>
      </div>

      {interpretation.hypothesis?.text ? (
        <div>
          <SectionLabel>Hypothesis</SectionLabel>
          <p className="mt-1.5 text-sm italic leading-relaxed text-slate-600">{interpretation.hypothesis.text}</p>
        </div>
      ) : null}
    </div>
  );
}

// The card as it was before interpretations: used whenever a card has none.
function Details({ item, steps }) {
  const [open, setOpen] = useState(false);
  return (
    <>
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
              <SectionLabel>Why it matters</SectionLabel>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-700">
                <Markup text={item.why} />
              </p>
            </div>
          ) : null}

          {steps.length > 0 ? (
            <div>
              <SectionLabel>Recommended next steps</SectionLabel>
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
    </>
  );
}

export default function ChangeCard({ item, isNew }) {
  const unverified = Boolean(item.unverified);
  const steps = item.steps?.length ? item.steps : item.action ? [item.action] : [];
  const interpretation = !unverified && item.interpretation ? item.interpretation : null;

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

      {item.category_label ? (
        <div className="mt-3">
          <CategoryChip item={item} />
        </div>
      ) : null}

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
          <div className="mb-2">
            <SectionLabel>
              {unverified ? "What's claimed" : interpretation ? 'Verified fact · from the pricing page' : 'What changed'}
            </SectionLabel>
          </div>
          <div className="space-y-2">
            {item.sources.map((source, index) => (
              <SourceBlock key={`${source.url}-${index}`} source={source} />
            ))}
          </div>
        </div>
      ) : null}

      {interpretation ? <Interpretation interpretation={interpretation} /> : <Details item={item} steps={steps} />}
    </article>
  );
}
