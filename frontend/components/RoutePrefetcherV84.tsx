'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const CORE_ROUTES = ['/signals', '/holdings', '/etfs', '/search'];

export default function RoutePrefetcherV84() {
  const router = useRouter();

  useEffect(() => {
    const prefetchAll = () => {
      for (const route of CORE_ROUTES) {
        try {
          router.prefetch(route);
        } catch {}
      }
    };

    const timer = window.setTimeout(prefetchAll, 300);
    const onVisible = () => {
      if (document.visibilityState === 'visible') prefetchAll();
    };

    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [router]);

  return null;
}
