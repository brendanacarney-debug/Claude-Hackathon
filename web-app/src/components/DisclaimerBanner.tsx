export function DisclaimerBanner({ children }: { children: string }) {
  return (
    <div className="rounded-[1.6rem] border border-[rgba(245,158,11,0.25)] bg-[rgba(254,243,199,0.6)] px-5 py-4 text-sm leading-6 text-[color:#7c5410]">
      {children}
    </div>
  );
}
