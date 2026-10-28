import React from 'react';
import { Outlet } from 'react-router-dom';
import TopBar from '@/components/TopBar';

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <TopBar />
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}