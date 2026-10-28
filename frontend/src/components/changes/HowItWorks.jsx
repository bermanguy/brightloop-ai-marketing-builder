import React, { useState } from 'react';
import { ChevronDown, FileCheck, GitCompare, Info, Scale, ScanSearch, ScanText } from 'lucide-react';
import { cn } from '@/lib/utils';
import Collapse from '@/components/Collapse';
import FlowStep from '@/components/changes/FlowStep';
import ScanVisual from '@/components/changes/ScanVisual';
import ReadIllustration from '@/components/changes/ReadIllustration';
import CompareIllustration from '@/components/changes/CompareIllustration';
import ReportIllustration from '@/components/changes/ReportIllustration';
import ConfidenceScale from '@/components/changes/ConfidenceScale';

const STEPS = [
  {
    key: 'scan',
    icon: ScanSearch,
    title: 'Scan',
    caption: 'Pricing pages every 6 hours, plus Hacker News.',
    visual: <ScanVisual />,
  },
  {
    key: 'read',
    icon: ScanText,
    title: 'Read',
    caption: 'Prices pulled and checked against the page.',
    visual: <ReadIllustration />,
  },
  {
    key: 'compare',
    icon: GitCompare,
    title: 'Compare',
    caption: 'Only real changes since the last check.',
    visual: <CompareIllustration />,
  },
  {
    key: 'judge',
    icon: Scale,
    title: 'Judge',
    caption: 'Rules, not AI, set confidence.',
    visual: <ConfidenceScale />,
  },
  {
    key: 'report',
    icon: FileCheck,
    title: 'Report',
    caption: 'A card with quote, link and next steps.',
    visual: <ReportIllustration />,
  },
];

export default function HowItWorks() {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left sm:px-5"
      >
        <Info className="h-4 w-4 shrink-0 text-indigo-500" />
        <span className="text-sm font-medium text-slate-900">How this works</span>
        <ChevronDown
          className={cn(
            'ml-auto h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200',
            open && 'rotate-180'
          )}
        />
      </button>

      <Collapse open={open}>
        <div className="grid grid-cols-1 gap-3 border-t border-slate-100 px-4 py-4 sm:grid-cols-2 sm:px-5 min-[900px]:grid-cols-5">
          {STEPS.map((step) => (
            <FlowStep key={step.key} icon={step.icon} title={step.title} caption={step.caption}>
              {step.visual}
            </FlowStep>
          ))}
        </div>
      </Collapse>
    </section>
  );
}