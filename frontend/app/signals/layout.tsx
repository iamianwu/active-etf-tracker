import SignalRangeTabsV75 from '@/components/SignalRangeTabsV75';

export default function SignalsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SignalRangeTabsV75 />
      {children}
    </>
  );
}
