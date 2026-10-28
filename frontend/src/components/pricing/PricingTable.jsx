import React from 'react';
import Markup from '@/components/Markup';

export default function PricingTable({ table }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
        <Markup text={table.title} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] border-collapse text-sm">
          <thead>
            <tr className="bg-slate-50/80 text-left">
              <th className="px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-slate-400">
                &nbsp;
              </th>
              {(table.columns || []).map((column, index) => (
                <th
                  key={`${column}-${index}`}
                  className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  <Markup text={column} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(table.rows || []).map((row, rowIndex) => (
              <tr key={`${row.label}-${rowIndex}`}>
                <td className="whitespace-nowrap px-4 py-2.5 text-slate-500">
                  <Markup text={row.label} />
                </td>
                {(row.values || []).map((value, valueIndex) => (
                  <td key={valueIndex} className="px-4 py-2.5 text-slate-700">
                    <Markup text={value} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}