import React from 'react';
import { cn } from '@/lib/utils';
import Markup from '@/components/Markup';

function Section({ title, last, children }) {
  return (
    <li className="flex gap-3">
      <div className="flex flex-col items-center">
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-indigo-300" />
        {last ? null : <span className="mt-1 w-px flex-1 bg-slate-200" />}
      </div>
      <div className={cn('min-w-0 flex-1', last ? 'pb-1' : 'pb-5')}>
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</div>
        <div className="mt-1.5 space-y-1.5">{children}</div>
      </div>
    </li>
  );
}

export default function RunDetails({ details }) {
  const data = details || {};
  const read = data.read || [];
  const notes = data.notes || [];
  const decided = data.decided || [];
  const skipped = data.skipped || [];
  const errors = data.errors || [];

  const sections = [];

  if (read.length > 0) {
    sections.push({
      title: 'Read',
      content: read.map((line, index) => (
        <p key={index} className="text-sm leading-relaxed text-slate-600">
          <Markup text={line} />
        </p>
      )),
    });
  }

  if (data.compared || notes.length > 0) {
    sections.push({
      title: 'Compared',
      content: (
        <>
          {data.compared ? (
            <p className="text-sm leading-relaxed text-slate-600">
              <Markup text={data.compared} />
            </p>
          ) : null}
          {notes.map((note, index) => (
            <p key={index} className="text-sm leading-relaxed text-slate-500">
              <Markup text={note} />
            </p>
          ))}
        </>
      ),
    });
  }

  if (data.found) {
    sections.push({
      title: 'Found',
      content: (
        <p className="text-sm leading-relaxed text-slate-600">
          <Markup text={data.found} />
        </p>
      ),
    });
  }

  if (decided.length > 0) {
    sections.push({
      title: 'Decided',
      content: decided.map((entry, index) => (
        <div
          key={index}
          className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2.5"
        >
          <div className="text-sm font-semibold leading-snug text-slate-800">
            <Markup text={entry.headline} />
          </div>
          {entry.rule ? (
            <div className="mt-1 text-xs leading-relaxed text-slate-500">
              <Markup text={entry.rule} />
            </div>
          ) : null}
          {entry.next_step ? (
            <div className="mt-1 text-xs leading-relaxed text-slate-500">
              Next step: <Markup text={entry.next_step} />
            </div>
          ) : null}
        </div>
      )),
    });
  }

  if (skipped.length > 0) {
    sections.push({
      title: 'Skipped',
      content: skipped.map((line, index) => (
        <p key={index} className="text-sm leading-relaxed text-slate-500">
          <Markup text={line} />
        </p>
      )),
    });
  }

  if (errors.length > 0) {
    sections.push({
      title: 'Errors',
      content: errors.map((line, index) => (
        <p key={index} className="text-sm leading-relaxed text-rose-600">
          <Markup text={line} />
        </p>
      )),
    });
  }

  if (sections.length === 0) {
    return (
      <div className="border-t border-slate-100 px-4 py-4 text-sm text-slate-500 sm:px-5">
        This run didn&apos;t record any details.
      </div>
    );
  }

  return (
    <div className="border-t border-slate-100 px-4 py-4 sm:px-5">
      <ol>
        {sections.map((section, index) => (
          <Section key={section.title} title={section.title} last={index === sections.length - 1}>
            {section.content}
          </Section>
        ))}
      </ol>
    </div>
  );
}