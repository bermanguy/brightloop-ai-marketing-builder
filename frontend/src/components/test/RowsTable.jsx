import React from 'react';
import { cn } from '@/lib/utils';
import Markup from '@/components/Markup';
import CompetitorAvatar from '@/components/CompetitorAvatar';

function rowItem(row) {
  return row.item || row;
}

function isSkipped(row) {
  if (row.result) return row.result === 'skipped';
  if (row.status) return row.status !== 'item';
  return !row.item;
}

function rowWhy(row) {
  const why = row.why ?? (isSkipped(row) ? row.reason || row.skipped : null);
  if (Array.isArray(why)) return why.filter(Boolean);
  if (typeof why === 'string' && why) return [why];
  return [];
}

export default function RowsTable({ rows }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full min-w-[680px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
            <th className="px-3 py-2 font-semibold">Id</th>
            <th className="px-3 py-2 font-semibold">Competitor</th>
            <th className="px-3 py-2 font-semibold">Result</th>
            <th className="px-3 py-2 font-semibold">Why</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const item = rowItem(row);
            const skipped = isSkipped(row);
            const why = rowWhy(row);
            const competitor = row.competitor || item.competitor;

            return (
              <tr key={`${row.id || 'row'}-${index}`} className="border-b border-slate-100 align-top last:border-0">
                <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs text-slate-500">
                  {row.id}
                </td>

                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <CompetitorAvatar competitor={competitor} size="sm" />
                    <div>
                      <div className="text-sm font-medium text-slate-900">{competitor}</div>
                      {row.type ? (
                        <div className="text-[11px] uppercase tracking-wide text-slate-400">
                          {row.type}
                        </div>
                      ) : null}
                    </div>
                  </div>
                </td>

                <td className="px-3 py-2.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold',
                        skipped
                          ? 'border-slate-200 bg-slate-50 text-slate-500'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      )}
                    >
                      {skipped ? 'Skipped' : 'Item'}
                    </span>
                    {item.unverified ? (
                      <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                        Unverified
                      </span>
                    ) : null}
                  </div>
                  {item.headline ? (
                    <div className="mt-1.5 text-sm leading-snug text-slate-700">
                      <Markup text={item.headline} />
                    </div>
                  ) : null}
                </td>

                <td className="px-3 py-2.5">
                  {why.length > 0 ? (
                    <ul className="space-y-1 text-sm leading-relaxed text-slate-600">
                      {why.map((line, lineIndex) => (
                        <li key={lineIndex} className="flex gap-2">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-300" />
                          <span>
                            <Markup text={line} />
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}