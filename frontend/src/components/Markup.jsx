import React from 'react';

const STRIKE_PATTERN = /~~([^~]+)~~/g;

/**
 * Renders text exactly as the engine gave it, turning ~~like this~~ into a
 * crossed-out price on the competitor's page.
 */
export default function Markup({ text, className }) {
  if (text === null || text === undefined) return null;

  const value = String(text);
  const parts = [];
  let lastIndex = 0;
  let match;

  STRIKE_PATTERN.lastIndex = 0;
  while ((match = STRIKE_PATTERN.exec(value)) !== null) {
    if (match.index > lastIndex) parts.push(value.slice(lastIndex, match.index));
    parts.push(
      <s key={`${match.index}-${match[1]}`} className="text-slate-400">
        {match[1]}
      </s>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < value.length) parts.push(value.slice(lastIndex));

  return <span className={className}>{parts.length ? parts : value}</span>;
}