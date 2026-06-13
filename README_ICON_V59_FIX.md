# v59 Icon Fix

This patch places icon files in both `frontend/public/` and Next.js App Router special icon paths under `frontend/app/`.
It also patches `frontend/app/layout.tsx` metadata so browser favicon and iOS Add to Home Screen can detect the icon.

After deployment, remove the old iPhone Home Screen shortcut and add it again. iOS caches old icons aggressively.
