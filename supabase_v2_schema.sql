create table if not exists stock_price_history (
  stock_code text not null,
  trade_date date not null,
  open double precision,
  high double precision,
  low double precision,
  close double precision,
  volume double precision,
  change_pct double precision,
  market text,
  updated_at text,
  primary key (stock_code, trade_date)
);

create table if not exists institutional_flows (
  stock_code text not null,
  trade_date date not null,
  foreign_net double precision,
  investment_trust_net double precision,
  dealer_net double precision,
  total_net double precision,
  source text,
  updated_at text,
  primary key (stock_code, trade_date, source)
);

create index if not exists idx_stock_price_history_code_date
on stock_price_history(stock_code, trade_date);

create index if not exists idx_institutional_flows_code_date
on institutional_flows(stock_code, trade_date);

alter table stock_price_history enable row level security;
alter table institutional_flows enable row level security;

drop policy if exists "Public read stock_price_history" on stock_price_history;
drop policy if exists "Public read institutional_flows" on institutional_flows;

create policy "Public read stock_price_history"
on stock_price_history for select
using (true);

create policy "Public read institutional_flows"
on institutional_flows for select
using (true);
