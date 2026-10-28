import React, { useEffect, useState } from 'react';
import { Bell, ChevronDown, Mail, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { fetchAlertSettings } from '@/api/pricewatch';
import CompetitorAvatar from '@/components/CompetitorAvatar';

const COMPANIES = ['Lovable', 'Bolt', 'Replit', 'v0'];
const LEVELS = [
  { value: '0.9', label: '0.9 · own pricing page' },
  { value: '0.6', label: '0.6 · own site' },
  { value: '0.4', label: '0.4 · third party' },
  { value: '0.2', label: '0.2 · everything' },
];

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
      <input
        type="checkbox"
        className="sr-only"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <Icon className="h-4 w-4" />
      {label}
    </label>
  );
}

// Alerts for a test upload: off by default; sent only when a channel is ticked.
export default function AlertOptions({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    fetchAlertSettings().then(setSettings).catch(() => setSettings(null));
  }, []);

  const set = (patch) => onChange({ ...value, ...patch });
  const toggleChannel = (channel, on) =>
    set({ channels: on ? [...value.channels, channel] : value.channels.filter((c) => c !== channel) });
  const toggleCompany = (name) =>
    set({
      competitors: value.competitors.includes(name)
        ? value.competitors.filter((c) => c !== name)
        : [...value.competitors, name],
    });
  const emailOn = value.channels.includes('email');

  return (
    <div className="mt-4 rounded-lg border border-slate-200">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-slate-700"
      >
        <Bell className="h-4 w-4 text-indigo-500" />
        Also send the result as an alert
        <span className="text-xs font-normal text-slate-400">
          {value.channels.length ? `on: ${value.channels.join(' + ')}` : 'off by default'}
        </span>
        <ChevronDown className={cn('ml-auto h-4 w-4 text-slate-400 transition-transform', open && 'rotate-180')} />
      </button>

      {open ? (
        <div className="space-y-4 border-t border-slate-100 px-3 py-3">
          <div className="flex flex-wrap gap-2">
            <Toggle
              icon={Mail}
              label="Email"
              checked={emailOn}
              disabled={settings && !settings.email}
              hint={settings && !settings.email ? 'Email is not set up on the server.' : undefined}
              onChange={(on) => toggleChannel('email', on)}
            />
            <Toggle
              icon={MessageSquare}
              label="Slack"
              checked={value.channels.includes('slack')}
              disabled={settings && !settings.slack}
              hint={settings && !settings.slack ? 'Slack is not set up on the server.' : undefined}
              onChange={(on) => toggleChannel('slack', on)}
            />
          </div>

          {emailOn ? (
            <label className="block text-sm text-slate-600">
              Send email to
              <input
                type="email"
                value={value.emailTo}
                onChange={(event) => set({ emailTo: event.target.value })}
                placeholder={settings?.email_to ? `default: ${settings.email_to}` : 'you@company.com'}
                className="mt-1 block w-full max-w-sm rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:border-indigo-400 focus:outline-none"
              />
            </label>
          ) : null}

          <div className="flex flex-wrap items-center gap-4">
            <label className="text-sm text-slate-600">
              Minimum confidence{' '}
              <select
                value={value.minConfidence}
                onChange={(event) => set({ minConfidence: event.target.value })}
                className="ml-1 rounded-lg border border-slate-200 px-2 py-1 text-sm"
              >
                {LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap items-center gap-1.5 text-sm text-slate-600">
              Companies
              {COMPANIES.map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => toggleCompany(name)}
                  className={cn(
                    'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs',
                    value.competitors.includes(name)
                      ? 'border-indigo-300 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 text-slate-500'
                  )}
                >
                  <CompetitorAvatar competitor={name} size="sm" />
                  {name}
                </button>
              ))}
              <span className="text-xs text-slate-400">{value.competitors.length ? '' : '(all)'}</span>
            </div>
          </div>

          <p className="text-xs text-slate-500">
            Slack goes to this app&apos;s channel{settings?.slack_channel ? ` (${settings.slack_channel})` : ''}; email to
            the address above or this app&apos;s inbox. Alerts are marked TEST, sent at most once every 5 minutes and 20
            times a day. result.json doesn&apos;t change.
          </p>
        </div>
      ) : null}
    </div>
  );
}
