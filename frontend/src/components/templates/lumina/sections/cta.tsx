import { Sparkles } from "lucide-react";

export default function FinalCTA() {
  return (
    <section id="contact" className="px-6 md:px-12 lg:px-20 pb-20 md:pb-28">
      <div className="max-w-6xl mx-auto relative overflow-hidden rounded-3xl bg-foreground text-primary-foreground px-8 md:px-16 py-20 md:py-28">
        <div className="absolute inset-0 opacity-40 pointer-events-none bg-[image:var(--cta-glow)]" />
        <div className="relative text-center max-w-2xl mx-auto flex flex-col items-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary-foreground/15 bg-primary-foreground/5 px-4 py-1.5 text-[11px] font-semibold tracking-wide text-primary-foreground/90 uppercase shadow-sm">
            <Sparkles size={12} className="opacity-70" />
            Ready in under 5 minutes
          </div>
          <h2 className="mt-8 font-display text-4xl md:text-5xl lg:text-[4rem] leading-[1] tracking-tight">
            Put your busywork on{" "}
            <em className="italic text-primary-foreground/60">autopilot</em>.
          </h2>
          <p className="mt-6 text-primary-foreground/80 md:text-lg max-w-[500px] mx-auto leading-relaxed font-medium text-balance">
            Join 900+ teams replacing brittle scripts with intelligent agents.
            Start free, scale when it matters.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4 flex-wrap">
            <a
              href="#pricing"
              className="rounded-xl px-7 py-3.5 text-[15px] font-semibold bg-white text-foreground hover:bg-white/90 transition-all shadow-[0_2px_12px_rgba(255,255,255,0.15)] ring-1 ring-inset ring-black/5"
            >
              Start building free
            </a>
            <a
              href="#contact"
              className="rounded-xl px-7 py-3.5 text-[15px] font-medium border border-primary-foreground/20 text-primary-foreground hover:bg-primary-foreground/10 transition-colors backdrop-blur-sm"
            >
              Talk to sales
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
