import React from 'react';

// Informational counts for the current date and company filter, from the engine's summary. They count detected
// changes (events, not unique business issues) and include cards hidden from Focused view. Every card is either
// source verified or unverified, so Total = Source verified + Unverified.
export default function SummaryCounters({ total = 0, verified = 0, unverified = 0 }) {
  const counters = [
    { label: 'Total changes', value: total },
    { label: 'Source verified', value: verified },
    { label: 'Unverified', value: unverified },
  ];
  return (
    <dl className="grid grid-cols-3 gap-2 sm:gap-3">
      {counters.map((counter) => (
        <div key={counter.label} className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm sm:px-4">
          <dt className="text-[11px] font-medium uppercase leading-tight tracking-wide text-slate-500">{counter.label}</dt>
          <dd className="mt-0.5 text-lg font-semibold leading-tight tracking-tight text-slate-900 sm:text-xl">{counter.value}</dd>
        </div>
      ))}
    </dl>
  );
}
