import React from 'react';
import { AlertTriangle, Bell, Download } from 'lucide-react';
import RowsTable from '@/components/test/RowsTable';
import ChangeCard from '@/components/changes/ChangeCard';

export default function TestResults({ data }) {
  const result = data.result || data;
  const summary = data.summary || null;
  const rows = data.rows || [];
  const items = result.items || [];
  const runErrors = result.run?.errors || [];
  const alerts = data.alerts || [];

  const download = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'result.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        {summary ? (
          <p className="text-sm font-medium text-slate-700">
            {summary.signals} signals in the file → {summary.items} items, {summary.skipped} skipped,{' '}
            {summary.errors} errors
          </p>
        ) : null}

        <button
          type="button"
          onClick={download}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
        >
          <Download className="h-3.5 w-3.5" />
          Download result.json
        </button>
      </div>

      {alerts.length > 0 ? (
        <div className="flex items-start gap-2 rounded-xl border border-indigo-200 bg-indigo-50/60 px-4 py-3 text-sm text-indigo-900">
          <Bell className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
          <ul className="space-y-0.5">
            {alerts.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {rows.length > 0 ? <RowsTable rows={rows} /> : null}

      {runErrors.length > 0 ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-red-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            Run errors
          </div>
          <ul className="mt-2 space-y-1 text-sm leading-relaxed text-red-800">
            {runErrors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {items.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Items, as the Changes tab shows them
          </h2>
          {items.map((item) => (
            <ChangeCard key={item.id} item={item} />
          ))}
        </section>
      ) : null}
    </div>
  );
}