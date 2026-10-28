import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Image } from '@/components/ui/image';
import { competitorStyle } from '@/lib/competitors';

const SIZES = {
  sm: { box: 'h-5 w-5', text: 'text-[9px]' },
  md: { box: 'h-8 w-8', text: 'text-[11px]' },
  lg: { box: 'h-10 w-10', text: 'text-sm' },
};

export default function CompetitorAvatar({ competitor, size = 'md', className }) {
  const { logo, initials, accentText } = competitorStyle(competitor);
  const [failedLogo, setFailedLogo] = useState(null);
  const dims = SIZES[size] || SIZES.md;
  const showLogo = Boolean(logo) && failedLogo !== logo;

  return (
    <span
      className={cn(
        'inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full border border-slate-200 bg-white',
        dims.box,
        className
      )}
    >
      {showLogo ? (
        <Image
          src={logo}
          alt=""
          fittingType="fit"
          onError={() => setFailedLogo(logo)}
          className="h-[65%] w-[65%]"
        />
      ) : (
        <span className={cn('font-semibold leading-none', accentText, dims.text)}>{initials}</span>
      )}
    </span>
  );
}