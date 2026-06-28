export const revalidate = 60;

import { getEtfListRows } from '@/lib/etfData';
import { REFERENCE_ETFS } from '@/lib/referenceEtfs';
import EtfListClient from '@/components/EtfListClient';

export default async function EtfsPage() {
  const activeRows = await getEtfListRows();

  const active = (activeRows || []).map((r: any) => ({
    ...r,
    etf_group: 'active',
  }));

  const reference = REFERENCE_ETFS.map((r) => ({
    ...r,
    etf_group: 'reference',
    etf_code: r.code,
    etf_name: r.name,
    reference_role: r.role,
    region: r.market,
  }));

  return <EtfListClient rows={[...active, ...reference]} />;
}
