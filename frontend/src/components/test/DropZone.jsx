import React, { useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function DropZone({ file, onFile, error }) {
  const inputRef = useRef(null);
  const [over, setOver] = useState(false);

  const pick = (files) => {
    const next = files && files[0];
    if (next) onFile(next);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setOver(false);
    pick(event.dataTransfer.files);
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".json,application/json"
        className="hidden"
        onChange={(event) => pick(event.target.files)}
      />

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={handleDrop}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors',
          over
            ? 'border-indigo-400 bg-indigo-50/70'
            : 'border-slate-200 bg-slate-50/60 hover:border-indigo-200 hover:bg-slate-50'
        )}
      >
        <UploadCloud className={cn('h-6 w-6', over ? 'text-indigo-500' : 'text-slate-400')} />
        <span className="text-sm font-medium text-slate-800">
          {file ? file.name : 'Drop a cases.json file here'}
        </span>
        <span className="text-xs text-slate-500">
          {file ? 'Click to choose a different file.' : 'or click to choose one'}
        </span>
      </div>

      {error ? <p className="mt-2 text-xs font-medium text-red-600">{error}</p> : null}
    </div>
  );
}