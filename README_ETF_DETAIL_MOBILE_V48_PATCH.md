# ETF Detail Mobile V48 Patch

Fix mobile table alignment by flattening header/body rows into the same CSS grid parent.

Changes:
- Holdings table: header and rows now share one grid column system.
- Operation table: same alignment method.
- Sticky header cells are applied per column to prevent iPhone Safari offset.
- Modal open hides sticky header cells to avoid overlay.

Deploy URL test:
- /etf/00400A?tab=holdings&v=48
- /etf/00400A?tab=operation&v=48
