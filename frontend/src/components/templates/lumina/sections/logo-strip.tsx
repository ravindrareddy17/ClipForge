const LOGOS = [
  "Linear", "Vercel", "Stripe", "Notion", "Figma", "Loom",
  "Ramp", "Mercury", "Cursor", "Anthropic", "Retool", "Arc",
];

export default function LogoStrip() {
  return (
    <section className="py-16 md:py-20 border-y border-border bg-white">
      <p className="text-center text-xs uppercase tracking-[0.18em] text-muted-foreground">
        Trusted by teams shipping the future
      </p>
      <div className="mt-8 overflow-hidden [mask-image:var(--mask-fade-x)] [-webkit-mask-image:var(--mask-fade-x)]">
        <div className="lumina-marquee flex items-center gap-16 px-8">
          {[...LOGOS, ...LOGOS].map((name, i) => (
            <span
              key={i}
              className="font-display text-2xl md:text-[28px] text-muted-foreground/70 whitespace-nowrap"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
