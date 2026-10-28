import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Radar } from 'lucide-react';
import { cn } from '@/lib/utils';
import FreshnessBadge from '@/components/FreshnessBadge';
import CheckNowButton from '@/components/CheckNowButton';

const TABS = [
  { to: '/', label: 'Changes', end: true },
  { to: '/pricing', label: 'Current pricing' },
  { to: '/runs', label: 'Run log' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/test', label: 'Test upload' },
];

export default function TopBar() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
          <Link to="/" className="order-1 flex items-center gap-2.5 transition-opacity hover:opacity-80">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
              <Radar className="h-4 w-4" />
            </span>
            <span className="text-sm font-semibold tracking-tight text-slate-900">
              Brightloop Pricing Watch
            </span>
          </Link>

          <nav className="order-3 flex w-full items-center gap-1 overflow-x-auto sm:order-2 sm:w-auto">
            {TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.end}
                className={({ isActive }) =>
                  cn(
                    'whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  )
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>

          <div className="order-2 ml-auto flex items-center gap-2 sm:order-3">
            <CheckNowButton />
            <FreshnessBadge />
          </div>
        </div>
      </div>
    </header>
  );
}