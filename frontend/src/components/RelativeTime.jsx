import React, { useEffect, useState } from 'react';
import { exactTime, relativeTime } from '@/lib/time';

export default function RelativeTime({ value, prefix = '', suffix = '', className }) {
  const [, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick((tick) => tick + 1), 60000);
    return () => clearInterval(id);
  }, []);

  if (!value) return null;

  return (
    <time dateTime={value} title={exactTime(value)} className={className}>
      {prefix}
      {relativeTime(value)}
      {suffix}
    </time>
  );
}