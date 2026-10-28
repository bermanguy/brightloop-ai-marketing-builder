import React, { useState } from 'react';
import { Loader2, Play } from 'lucide-react';
import { runTest } from '@/api/pricewatch';
import TestHowItWorks from '@/components/test/TestHowItWorks';
import DropZone from '@/components/test/DropZone';
import TestResults from '@/components/test/TestResults';
import AlertOptions from '@/components/test/AlertOptions';
import ErrorState from '@/components/ErrorState';

export default function TestUpload() {
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState({ channels: [], minConfidence: '0.6', competitors: [], emailTo: '' });

  const choose = (next) => {
    setData(null);
    setError(null);

    if (!/\.json$/i.test(next.name)) {
      setFile(null);
      setFileError('Choose a .json file.');
      return;
    }

    setFileError(null);
    setFile(next);
  };

  const run = async (event) => {
    if (event) event.preventDefault();
    if (!file || running) return;

    setRunning(true);
    setError(null);
    setData(null);

    try {
      setData(await runTest(file, alerts));
    } catch (err) {
      setError(err.message || 'The pricing engine could not be reached.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <TestHowItWorks />

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <form onSubmit={run}>
          <DropZone file={file} onFile={choose} error={fileError} />

          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              One JSON file, nothing stored: the other tabs don&apos;t change.
            </p>
            <button
              type="submit"
              disabled={!file || running}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Run test
            </button>
          </div>

          <AlertOptions value={alerts} onChange={setAlerts} />
        </form>
      </section>

      {error ? <ErrorState message={error} onRetry={run} /> : null}
      {data ? <TestResults data={data} /> : null}
    </div>
  );
}