import React, { useEffect, useState } from 'react';
import { ChevronDown, Loader2, Mail, MessageSquare, Plus, Settings2, X } from 'lucide-react';
import Collapse from '@/components/Collapse';
import { cn } from '@/lib/utils';
import { fetchAlertSettings, fetchAlertLog, saveAlertSettings } from '@/api/pricewatch';
import { exactTime, relativeTime } from '@/lib/time';
import CompetitorAvatar from '@/components/CompetitorAvatar';
import ErrorState from '@/components/ErrorState';

const COMPANIES = ['Lovable', 'Bolt', 'Replit', 'v0'];
const LEVELS = [
  { value: 0.9, label: '0.9 · own pricing page' },
  { value: 0.6, label: '0.6 · own site' },
  { value: 0.4, label: '0.4 · third party' },
  { value: 0.2, label: '0.2 · everything' },
];
const MAX_EXTRA = 3;
const TRIGGERS = { schedule: 'Scheduled', 'backup schedule': 'Scheduled (backup)', manual: 'Check now', API: 'API', 'test upload': 'Test upload' };

function Toggle({ icon: Icon, label, checked, disabled, hint, onChange }) {
  return (
    <label
      title={hint}
      className={cn(
        'inline-flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors',
        checked ? 'border-indigo-300 bg-indigo-50 text-indigo-700' : 'border-slate-200 bg-white text-slate-600',
        disabled && 'cursor-not-allowed opacity-50'
      )}
    >
      <input type="checkbox" className="sr-only" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      {Icon ? <Icon className="h-4 w-4" /> : null}
      {label}
      <span className="text-xs">{checked ? 'on' : 'off'}</span>
    </label>
  );
}

function Row({ label, children }) {
  return (
    <div className="flex flex-col gap-2 border-t border-slate-100 py-3 first:border-t-0 sm:flex-row sm:items-center">
      <div className="w-44 shrink-0 text-sm font-medium text-slate-700">{label}</div>
      <div className="flex flex-1 flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}

function SettingsPanel({ settings, onSave, saving, error }) {
  const [address, setAddress] = useState('');
  const toggleCompany = (name) => {
    const next = settings.competitors.includes(name)
      ? settings.competitors.filter((c) => c !== name)
      : [...settings.competitors, name];
    onSave({ competitors: next });
  };
  const add = async (event) => {
    event.preventDefault();
    if (!address.trim()) return;
    if (await onSave({ add_email: address.trim() })) setAddress('');
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="mb-2 flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-indigo-500" />
        <h2 className="text-sm font-semibold text-slate-900">Settings for live runs</h2>
        <span className="ml-auto text-xs text-slate-400">
          {saving ? (
            <span className="inline-flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Saving</span>
          ) : settings.changed_at ? (
            `Saved · changed ${relativeTime(settings.changed_at)}`
          ) : (
            'Each change saves straight away'
          )}
        </span>
      </div>

      <Row label="Channels">
        <Toggle
          icon={Mail}
          label="Email"
          checked={settings.email && settings.email_on}
          disabled={!settings.email || saving}
          hint={!settings.email ? 'Email is not set up on the server.' : undefined}
          onChange={(on) => onSave({ email_on: on })}
        />
        <Toggle
          icon={MessageSquare}
          label={`Slack${settings.slack_channel ? ` · ${settings.slack_channel}` : ''}`}
          checked={settings.slack && settings.slack_on}
          disabled={!settings.slack || saving}
          hint={!settings.slack ? 'Slack is not set up on the server.' : undefined}
          onChange={(on) => onSave({ slack_on: on })}
        />
      </Row>

      <Row label="Send for">
        <Toggle label="Scheduled runs" checked={settings.on_schedule} disabled={saving} onChange={(on) => onSave({ on_schedule: on })} />
        <Toggle label="Check now" checked={settings.on_check_now} disabled={saving} onChange={(on) => onSave({ on_check_now: on })} />
      </Row>

      <Row label="Minimum confidence">
        <select
          value={String(settings.min_confidence)}
          disabled={saving}
          onChange={(e) => onSave({ min_confidence: Number(e.target.value) })}
          className="rounded-lg border border-slate-200 px-2 py-1 text-sm"
        >
          {LEVELS.map((level) => (
            <option key={level.value} value={String(level.value)}>{level.label}</option>
          ))}
        </select>
      </Row>

      <Row label="Companies">
        {COMPANIES.map((name) => (
          <button
            key={name}
            type="button"
            disabled={saving}
            onClick={() => toggleCompany(name)}
            className={cn(
              'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs',
              settings.competitors.includes(name) ? 'border-indigo-300 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-500'
            )}
          >
            <CompetitorAvatar competitor={name} size="sm" />
            {name}
          </button>
        ))}
        <span className="text-xs text-slate-400">{settings.competitors.length ? '' : '(all)'}</span>
      </Row>

      <Row label="Email recipients">
        {settings.email_to ? (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600" title="Set on the server">
            {settings.email_to} · owner
          </span>
        ) : null}
        {settings.extra_emails.map((masked, index) => (
          <span key={`${masked}-${index}`} className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs text-indigo-700">
            {masked}
            <button type="button" disabled={saving} onClick={() => onSave({ remove_email: index })} aria-label={`Remove ${masked}`}>
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        {settings.extra_emails.length < MAX_EXTRA ? (
          <form onSubmit={add} className="flex items-center gap-1.5">
            <input
              type="email"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="you@company.com"
              className="w-48 rounded-lg border border-slate-200 px-2.5 py-1 text-sm focus:border-indigo-400 focus:outline-none"
            />
            <button
              type="submit"
              disabled={saving || !address.trim()}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <Plus className="h-3 w-3" /> Add
            </button>
          </form>
        ) : (
          <span className="text-xs text-slate-400">Up to {MAX_EXTRA} extra addresses; remove one to add another.</span>
        )}
      </Row>

      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      <p className="mt-2 text-xs text-slate-500">
        After each live run, its new changes that pass these filters go to each channel that is on. Keys stay on the server;
        addresses are shown masked. Every change here is noted in the alert log.
      </p>
    </section>
  );
}

// What happened to an alert, from what each channel answered: sent, held back by the settings, or failed.
function alertStatus(entry) {
  const lines = entry.outcome || [];
  if (lines.some((line) => line.startsWith('Nothing sent') || line.startsWith('No alert sent'))) {
    return { label: 'Held back', dot: 'bg-slate-300', text: 'text-slate-500' };
  }
  if (lines.some((line) => /failed|not set up/i.test(line))) {
    return { label: 'Failed', dot: 'bg-rose-500', text: 'text-rose-600' };
  }
  return { label: 'Sent', dot: 'bg-emerald-500', text: 'text-emerald-700' };
}

function Detail({ label, children }) {
  return (
    <div className="flex gap-3 text-xs">
      <span className="w-28 shrink-0 text-slate-400">{label}</span>
      <span className="text-slate-700">{children}</span>
    </div>
  );
}

function LogEntry({ entry }) {
  const [open, setOpen] = useState(false);
  const when = (
    <span className="w-[86px] shrink-0 text-sm font-medium text-slate-700" title={exactTime(entry.at)}>
      {relativeTime(entry.at)}
    </span>
  );

  if (entry.kind === 'settings') {
    return (
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5">
        <Settings2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
        {when}
        <span className="text-xs text-slate-500">{(entry.outcome || []).join(' ')}</span>
      </div>
    );
  }

  const status = alertStatus(entry);
  const sent = entry.sent || [];
  const companies = [...new Set(sent.map((item) => item.competitor).filter(Boolean))];

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3.5 text-left"
      >
        <span className={cn('h-2.5 w-2.5 shrink-0 rounded-full', status.dot)} title={status.label} />
        {when}
        <span className="inline-flex shrink-0 items-center gap-1.5">
          <span className="text-[11px] text-slate-400">Started by</span>
          <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">
            {TRIGGERS[entry.trigger] || entry.trigger}
          </span>
          {entry.test ? (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-semibold text-amber-700">TEST</span>
          ) : null}
        </span>
        <span className="flex items-center gap-1">
          {companies.map((name) => (
            <CompetitorAvatar key={name} competitor={name} size="sm" />
          ))}
        </span>
        <span className="ml-auto flex items-center gap-4 text-xs text-slate-500">
          <span className="whitespace-nowrap">
            {sent.length} of {entry.changes} {entry.changes === 1 ? 'change' : 'changes'}
          </span>
          <span className="whitespace-nowrap">{entry.channels?.length ? entry.channels.join(' + ') : 'no channel'}</span>
          <span className={cn('whitespace-nowrap font-medium', status.text)}>{status.label}</span>
          <ChevronDown
            className={cn('h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200', open && 'rotate-180')}
          />
        </span>
      </button>

      <Collapse open={open}>
        <div className="space-y-3 border-t border-slate-100 px-4 py-3">
          {sent.length ? (
            <ul className="space-y-1.5">
              {sent.map((item, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-slate-700">
                  <CompetitorAvatar competitor={item.competitor} size="sm" />
                  <span className="flex-1">{item.headline}</span>
                  <span className="shrink-0 text-xs text-slate-500">
                    {item.confidence}
                    {item.unverified ? ' · unverified' : ''}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No change passed the filters.</p>
          )}
          <div className="space-y-1">
            {entry.recipients?.length ? <Detail label="Email to">{entry.recipients.join(', ')}</Detail> : null}
            {entry.slack_channel ? <Detail label="Slack channel">{entry.slack_channel}</Detail> : null}
            <Detail label="Filters">
              confidence {entry.min_confidence} or more · {entry.competitors?.length ? entry.competitors.join(', ') : 'all companies'}
            </Detail>
            <Detail label="Result">{(entry.outcome || []).join(' ')}</Detail>
            <Detail label="Time">{exactTime(entry.at)}</Detail>
          </div>
        </div>
      </Collapse>
    </div>
  );
}

export default function Alerts() {
  const [settings, setSettings] = useState(null);
  const [log, setLog] = useState(null);
  const [error, setError] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    Promise.all([fetchAlertSettings(), fetchAlertLog()])
      .then(([s, l]) => {
        if (cancelled) return;
        setSettings(s);
        setLog(Array.isArray(l) ? l : []);
      })
      .catch((err) => !cancelled && setError(err.message || 'The pricing engine could not be reached.'));
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const save = async (changes) => {
    setSaving(true);
    setSaveError(null);
    try {
      setSettings(await saveAlertSettings(changes));
      fetchAlertLog().then((l) => setLog(Array.isArray(l) ? l : [])).catch(() => {});
      return true;
    } catch (err) {
      setSaveError(err.message);
      return false;
    } finally {
      setSaving(false);
    }
  };

  if (error) return <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />;
  if (!settings) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading alerts
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SettingsPanel settings={settings} onSave={save} saving={saving} error={saveError} />
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">Alert log</h2>
        {log && log.length ? (
          log.map((entry, index) => <LogEntry key={`${entry.at}-${index}`} entry={entry} />)
        ) : (
          <p className="text-sm text-slate-500">No alerts yet. They appear here after a run with new changes, or a test upload with alerts on.</p>
        )}
      </section>
    </div>
  );
}
