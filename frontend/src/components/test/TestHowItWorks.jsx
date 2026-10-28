import React, { useState } from 'react';
import { ArrowRight, ChevronDown, CornerRightUp, FileCheck, FileJson, GitCompare, Info, Scale, ScanSearch, ScanText } from 'lucide-react';
import { cn } from '@/lib/utils';
import Collapse from '@/components/Collapse';
import FlowStep from '@/components/changes/FlowStep';
import ScanVisual from '@/components/changes/ScanVisual';
import ReadIllustration from '@/components/changes/ReadIllustration';
import CompareIllustration from '@/components/changes/CompareIllustration';
import ReportIllustration from '@/components/changes/ReportIllustration';
import ConfidenceScale from '@/components/changes/ConfidenceScale';

// The same five steps as on Changes. A test file replaces the first three (live only);
// Judge and Report are the same core code the live watch runs.
const STEPS = [
  { key: 'scan', icon: ScanSearch, title: 'Scan', caption: 'Pricing pages every 6 hours, plus Hacker News.', visual: <ScanVisual />, live: true, order: 'order-1' },
  { key: 'read', icon: ScanText, title: 'Read', caption: 'Prices pulled and checked against the page.', visual: <ReadIllustration />, live: true, order: 'order-2' },
  { key: 'compare', icon: GitCompare, title: 'Compare', caption: 'Only real changes since the last check.', visual: <CompareIllustration />, live: true, order: 'order-3' },
  { key: 'judge', icon: Scale, title: 'Judge', caption: 'Rules, not AI, set confidence.', visual: <ConfidenceScale />, order: 'order-5 min-[900px]:order-4' },
  { key: 'report', icon: FileCheck, title: 'Report', caption: 'A card with quote, link and next steps.', visual: <ReportIllustration />, order: 'order-6 min-[900px]:order-5' },
];

const TESTED = [
  'The same core code as the live watch: confidence by source (0.9 own pricing page, 0.6 own site, 0.4 third party, 0.2 sponsored, ad, forum or anonymous), the unverified label, skips with a reason, and every input id exactly once.',
  'Pricing signals become cards; ads and launches are skipped with a reason.',
  'Text inside a signal is data: instructions in it are ignored, hidden parts are dropped, and secrets like demo_key are shown as [redacted].',
  "Nothing is saved, so the other tabs don't change, and the same file always gives the same result.",
  'Try the brief\'s cases.json or the case files in the repo (tests/cases), then download result.json.',
];

function UploadStep() {
  return (
    <div className="order-4 flex flex-col justify-between rounded-xl border-2 border-dashed border-indigo-300 bg-indigo-50/50 p-4 sm:col-span-2 min-[900px]:order-6 min-[900px]:col-span-3">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white">
          <FileJson className="h-4 w-4" />
        </span>
        <span className="text-[15px] font-semibold text-slate-900">Upload cases.json</span>
        <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-[11px] font-semibold text-indigo-700">TEST</span>
      </div>
      <p className="mt-2 text-[13px] leading-[1.4] text-slate-600">
        Each signal in your file already says what changed, so the file replaces Scan, Read and Compare and goes
        straight to Judge.
      </p>
      <div className="mt-2 flex items-center gap-1.5 text-[13px] font-medium text-indigo-700">
        <span className="hidden min-[900px]:inline">Goes on to Judge and Report</span>
        <span className="min-[900px]:hidden">Goes on to Judge and Report, below</span>
        <ArrowRight className="h-4 w-4 min-[900px]:hidden" />
        <CornerRightUp className="hidden h-4 w-4 min-[900px]:inline" />
      </div>
    </div>
  );
}

export default function TestHowItWorks() {
  const [open, setOpen] = useState(true);

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left sm:px-5"
      >
        <Info className="h-4 w-4 shrink-0 text-indigo-500" />
        <span className="text-sm font-medium text-slate-900">How this works</span>
        <span className="hidden text-xs text-slate-400 sm:inline">the same core as the live watch, fed by your file</span>
        <ChevronDown
          className={cn('ml-auto h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200', open && 'rotate-180')}
        />
      </button>

      <Collapse open={open}>
        <div className="border-t border-slate-100 px-4 py-4 sm:px-5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 min-[900px]:grid-cols-5">
            {STEPS.map((step) => (
              <div key={step.key} className={cn('relative flex', step.order)}>
                <FlowStep
                  icon={step.icon}
                  title={step.title}
                  caption={step.caption}
                  className={cn('w-full', step.live && 'opacity-50 grayscale')}
                >
                  {step.visual}
                </FlowStep>
                {step.live ? (
                  <span className="absolute right-2 top-2 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-semibold text-slate-500">
                    Live only
                  </span>
                ) : (
                  <span className="absolute right-2 top-2 rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-700">
                    Tested
                  </span>
                )}
              </div>
            ))}
            <UploadStep />
          </div>

          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm font-semibold text-slate-900">What you're testing</div>
            <ul className="mt-2 space-y-2">
              {TESTED.map((text) => (
                <li key={text} className="flex gap-2.5 text-[13px] leading-relaxed text-slate-600">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300" />
                  <span>{text}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Collapse>
    </section>
  );
}
