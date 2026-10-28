import React, { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { fetchPricing } from '@/api/pricewatch';
import { hostLabel, withProtocol } from '@/lib/links';
import Markup from '@/components/Markup';
import RelativeTime from '@/components/RelativeTime';
import EmptyState from '@/components/EmptyState';
import ErrorState from '@/components/ErrorState';
import CompetitorAvatar from '@/components/CompetitorAvatar';
import PricingControls from '@/components/pricing/PricingControls';
import PlanCard from '@/components/pricing/PlanCard';
import PricingTable from '@/components/pricing/PricingTable';
import UnreadPageNotice from '@/components/pricing/UnreadPageNotice';
import PricingSkeleton from '@/components/pricing/PricingSkeleton';

export default function CurrentPricing() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [competitor, setCompetitor] = useState('');
  const [view, setView] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchPricing()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || 'The pricing engine could not be reached.');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const pages = data?.pages || [];
  const competitors = [];
  pages.forEach((page) => {
    if (!competitors.includes(page.competitor)) competitors.push(page.competitor);
  });

  const activeCompetitor = competitor || competitors[0] || '';
  const competitorPages = pages.filter((page) => page.competitor === activeCompetitor);

  const views = [];
  competitorPages.forEach((page) => {
    if (page.view && !views.includes(page.view)) views.push(page.view);
  });

  const opensOn = competitorPages.find((page) => page.opens_on)?.opens_on || null;
  const defaultView = views.includes(opensOn) ? opensOn : views[0];
  const activeView = views.length > 1 ? view || defaultView : null;
  const page = activeView
    ? competitorPages.find((item) => item.view === activeView)
    : competitorPages[0];

  const handleCompetitorChange = (name) => {
    setCompetitor(name);
    setView(null);
  };

  if (loading) return <PricingSkeleton />;
  if (error) return <ErrorState message={error} onRetry={() => setReloadKey((key) => key + 1)} />;
  if (pages.length === 0) {
    return (
      <EmptyState
        icon={ExternalLink}
        title="No pricing pages yet."
        description="The engine hasn't stored a reading yet. Check again from the pricing engine."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <CompetitorAvatar competitor={activeCompetitor} size="lg" />
        <h1 className="text-lg font-semibold tracking-tight text-slate-900">{activeCompetitor}</h1>
      </div>

      <PricingControls
        competitors={competitors}
        competitor={activeCompetitor}
        onCompetitorChange={handleCompetitorChange}
        views={views}
        view={activeView}
        opensOn={opensOn}
        onViewChange={setView}
      />

      {page ? (
        page.ok === false ? (
          <UnreadPageNotice page={page} />
        ) : (
          <>
            <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(230px,1fr))]">
              {(page.plans || []).map((plan, index) => (
                <PlanCard key={`${plan.name}-${index}`} plan={plan} />
              ))}
            </div>

            {(page.tables || []).map((table, index) => (
              <PricingTable key={`${table.title}-${index}`} table={table} />
            ))}
          </>
        )
      ) : null}

      {page ? (
        <footer className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-slate-200 pt-4 text-xs text-slate-500">
          <span>Source:</span>
          <a
            href={withProtocol(page.url)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-medium text-indigo-600 transition-colors hover:text-indigo-700 hover:underline"
          >
            <Markup text={hostLabel(page.url)} />
            <ExternalLink className="h-3 w-3" />
          </a>
          <span>·</span>
          <RelativeTime value={page.fetched_at} prefix="checked " />
        </footer>
      ) : null}
    </div>
  );
}