import React, { useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import Markup from '@/components/Markup';
import Collapse from '@/components/Collapse';

export default function PlanCard({ plan }) {
  const [optionsOpen, setOptionsOpen] = useState(false);
  const options = plan.options || [];

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">
        <Markup text={plan.name} />
      </div>

      <div className="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          <Markup text={plan.price} />
        </span>
        {plan.list_price ? (
          <s className="text-sm text-slate-400">{plan.list_price}</s>
        ) : null}
      </div>

      {plan.billing ? (
        <div className="mt-1.5 text-xs leading-relaxed text-slate-500">
          <Markup text={plan.billing} />
        </div>
      ) : null}

      {plan.includes?.length ? (
        <div className="mt-4 border-t border-slate-100 pt-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Includes
          </div>
          <ul className="mt-2 space-y-2">
            {plan.includes.map((line, index) => (
              <li key={index} className="flex gap-2 text-sm leading-relaxed text-slate-600">
                <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-indigo-500" />
                <Markup text={line} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {options.length > 0 ? (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <button
            type="button"
            onClick={() => setOptionsOpen((value) => !value)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 transition-colors hover:text-indigo-600"
          >
            <ChevronDown
              className={cn('h-3.5 w-3.5 transition-transform duration-200', optionsOpen && 'rotate-180')}
            />
            Credit options ({options.length})
          </button>

          <Collapse open={optionsOpen}>
            <ul className="mt-2 space-y-1.5">
              {options.map((option, index) => (
                <li key={index} className="text-sm text-slate-600">
                  <Markup text={option} />
                </li>
              ))}
            </ul>
          </Collapse>
        </div>
      ) : null}
    </div>
  );
}