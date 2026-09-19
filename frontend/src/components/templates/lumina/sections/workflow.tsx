import * as motion from "motion/react-client";
import { ArrowRight } from "lucide-react";

const STEPS = [
  {
    no: "01",
    title: "Connect your stack",
    body: "Authenticate Slack, Gmail, HubSpot, Notion, and 200+ apps in seconds. Bring your own model keys, or use ours.",
  },
  {
    no: "02",
    title: "Describe the outcome",
    body: "Write a prompt or sketch a flow. Lumina drafts the agent, picks the right tools, and proposes guardrails.",
  },
  {
    no: "03",
    title: "Deploy, monitor, improve",
    body: "Ship to staging or prod in one click. Inspect every run, replay failures, and roll back instantly.",
  },
];

export default function Workflow() {
  return (
    <section className="relative py-24 md:py-32 px-6 md:px-12 lg:px-20 bg-secondary/40 overflow-hidden">
      <div className="absolute inset-0 lumina-grid-bg opacity-50 pointer-events-none" />
      <div className="relative max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-xl"
          >
            <div className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              How it works
            </div>
            <h2 className="mt-5 font-display text-4xl md:text-5xl lg:text-6xl leading-[1] tracking-tight">
              From idea to deployed agent in <em className="italic">minutes</em>.
            </h2>
          </motion.div>
          <motion.a
            href="#"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.4, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="text-sm text-foreground inline-flex items-center gap-1 hover:underline"
          >
            See the full workflow <ArrowRight size={14} />
          </motion.a>
        </div>

        {/* Timeline */}
        <div className="mt-16 relative">
          {/* SVG connector spine — hidden on mobile */}
          <div className="hidden md:block absolute left-[calc(50%-0.5px)] top-0 bottom-0 w-px" aria-hidden>
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1 100" xmlns="http://www.w3.org/2000/svg">
              <line x1="0.5" y1="0" x2="0.5" y2="100" stroke="hsl(var(--border))" strokeWidth="1" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
            </svg>
          </div>

          <div className="flex flex-col gap-12 md:gap-0">
            {STEPS.map((s, i) => {
              const isLeft = i % 2 === 0;
              return (
                <motion.div
                  key={s.no}
                  initial={{ opacity: 0, x: isLeft ? -24 : 24 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{ duration: 0.55, delay: i * 0.12, ease: [0.22, 1, 0.36, 1] }}
                  className="md:grid md:grid-cols-2 md:gap-12 relative md:mb-14"
                >
                  {/* Text cell */}
                  <div className={isLeft ? "md:pr-10" : "md:order-last md:pl-10"}>
                    <div className="bg-background rounded-2xl p-7 border border-border h-full flex flex-col justify-center">
                      <span className="font-display text-5xl text-muted-foreground/40 leading-none">
                        {s.no}
                      </span>
                      <h3 className="mt-6 font-display text-2xl tracking-tight">{s.title}</h3>
                      <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{s.body}</p>
                    </div>
                  </div>

                  {/* Center node on the spine */}
                  <div className="hidden md:flex absolute left-1/2 top-8 -translate-x-1/2 items-center justify-center z-10">
                    <motion.div
                      initial={{ scale: 0.5, opacity: 0 }}
                      whileInView={{ scale: 1, opacity: 1 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.35, delay: i * 0.12 + 0.1, ease: [0.22, 1, 0.36, 1] }}
                      className="w-8 h-8 rounded-full bg-background border-2 border-accent flex items-center justify-center"
                    >
                      <span className="text-[11px] font-semibold text-accent tabular-nums">{i + 1}</span>
                    </motion.div>
                  </div>

                  {/* Visual cell */}
                  <div className={isLeft ? "hidden md:block md:pl-10" : "hidden md:block md:pr-10 md:order-first"}>
                    <div className="w-full h-full min-h-[220px] rounded-2xl bg-muted/20 border border-border/50 flex items-center justify-center relative overflow-hidden group">
                      <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                      <span className="text-sm font-medium text-muted-foreground/30 group-hover:text-muted-foreground/50 transition-colors">
                        Visual context
                      </span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
