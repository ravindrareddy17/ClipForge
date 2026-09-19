"use client";

import * as motion from "motion/react-client";

const reveal = {
  hidden: { opacity: 0, y: 20 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] as const },
  }),
};

function AgentMockup() {
  const rows = [
    { agent: "ops-monitor", status: "running", runs: "14.2k", ok: true },
    { agent: "support-triage", status: "running", runs: "9.8k", ok: true },
    { agent: "data-sync", status: "idle", runs: "3.1k", ok: false },
  ];
  return (
    <div className="lumina-bento-mockup mt-8 rounded-2xl border border-border/60 overflow-hidden bg-secondary/20 shadow-sm">
      <div className="px-5 py-3 border-b border-border/60 flex items-center justify-between bg-white/50">
        <span className="text-[11px] font-semibold text-muted-foreground/80 tracking-widest uppercase">
          Agent activity
        </span>
        <span className="text-[11px] font-medium text-muted-foreground/80 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          live
        </span>
      </div>
      {rows.map((r, i) => (
        <div
          key={r.agent}
          className="px-5 py-3.5 flex items-center justify-between border-b border-border/60 last:border-0 lumina-row-reveal bg-white/30"
          style={{ animationDelay: `${i * 0.4}s` }}
        >
          <div className="flex items-center gap-3">
            <span
              className={`w-2 h-2 rounded-full flex-shrink-0 ${r.ok ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)] lumina-pulse-dot" : "bg-muted-foreground/30"}`}
            />
            <span className="text-sm font-medium text-foreground tracking-tight">
              {r.agent}
            </span>
          </div>
          <div className="flex items-center gap-5">
            <span className="text-xs font-medium text-muted-foreground tabular-nums tracking-tight">
              {r.runs} runs
            </span>
            <span
              className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-md ${
                r.ok
                  ? "bg-emerald-500/10 text-emerald-600"
                  : "bg-secondary text-muted-foreground"
              }`}
            >
              {r.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Features() {
  return (
    <section
      id="features"
      className="py-24 md:py-32 px-6 md:px-12 lg:px-20 bg-background"
    >
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-60px" }}
          custom={0}
          variants={reveal}
          className="max-w-2xl"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-secondary/50 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-foreground" />
            Platform
          </div>
          <h2 className="mt-6 font-display text-4xl md:text-5xl lg:text-[3.5rem] leading-[1] tracking-tight">
            Everything you need to ship{" "}
            <em className="italic text-muted-foreground">intelligent</em>{" "}
            software.
          </h2>
          <p className="mt-5 text-muted-foreground text-lg md:text-xl max-w-[600px] leading-relaxed font-medium text-balance">
            A single platform for building, deploying, and governing agents in
            production — purpose-built for teams that move fast and stay safe.
          </p>
        </motion.div>

        {/* Bento grid */}
        <div className="mt-16 lumina-bento-grid">
          {/* Cell A — hero, spans 2 cols, tall */}
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            custom={1}
            variants={reveal}
            className="lumina-bento-cell lumina-bento-a relative overflow-hidden bg-gradient-to-br from-background to-secondary/30 border border-border/80 shadow-[0_4px_30px_rgba(0,0,0,0.03)] rounded-3xl p-8 md:p-10 flex flex-col"
          >
            <div className="absolute top-0 right-0 -mr-20 -mt-20 w-72 h-72 rounded-full bg-foreground/[0.02] blur-3xl pointer-events-none" />
            <div className="relative z-10 h-10 w-10 rounded-lg bg-secondary flex items-center justify-center border border-border">
              <svg
                viewBox="0 0 18 18"
                className="w-5 h-5 text-foreground opacity-90"
              >
                <circle cx="9" cy="9" r="3" fill="currentColor" />
                <path
                  d="M9 1v2M9 15v2M1 9h2M15 9h2M3.22 3.22l1.42 1.42M13.36 13.36l1.42 1.42M3.22 14.78l1.42-1.42M13.36 4.64l1.42-1.42"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  fill="none"
                />
              </svg>
            </div>
            <h3 className="mt-8 font-display text-2xl md:text-3xl tracking-tight leading-[1.05]">
              Autonomous agents that plan, act, and verify.
            </h3>
            <p className="mt-4 text-base text-muted-foreground leading-relaxed max-w-[400px]">
              Spin up specialized agents for ops, sales, and support. No
              babysitting required. Our orchestration engine handles state and
              retries.
            </p>
            <AgentMockup />
          </motion.div>

          {/* Cell B — secondary, 1 col, accent number */}
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            custom={2}
            variants={reveal}
            className="lumina-bento-cell lumina-bento-b relative overflow-hidden bg-gradient-to-bl from-secondary/40 to-background rounded-3xl p-8 md:p-10 flex flex-col justify-between border border-border/80 shadow-sm"
          >
            <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_bottom_right,rgba(0,0,0,0.02)_0%,transparent_60%)]" />
            <div className="relative z-10">
              <div className="h-10 w-10 rounded-lg bg-foreground text-primary-foreground flex items-center justify-center shadow-sm">
                <svg
                  viewBox="0 0 18 18"
                  className="w-5 h-5 fill-none stroke-current"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <path d="M3 9h12M9 3l6 6-6 6" />
                </svg>
              </div>
              <h3 className="mt-8 font-display text-2xl tracking-tight leading-[1.05]">
                Composable workflows
              </h3>
              <p className="mt-3 text-base text-muted-foreground leading-relaxed">
                Drag, branch, and version multi-step flows. Roll back any change
                with a single click.
              </p>
            </div>
            <div className="relative z-10 mt-12 font-display text-[5rem] text-foreground/5 leading-none select-none tracking-tighter">
              200+
            </div>
            <p className="relative z-10 text-sm font-medium text-muted-foreground mt-2">
              integrations available
            </p>
          </motion.div>

          {/* Cell C — full-width stat bar */}
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            custom={3}
            variants={reveal}
            className="lumina-bento-cell lumina-bento-c rounded-3xl border border-border bg-white shadow-sm overflow-hidden"
          >
            <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-border h-full">
              {[
                {
                  stat: "SOC 2 Type II",
                  label: "Enterprise-grade trust",
                  sub: "HIPAA & GDPR ready",
                },
                {
                  stat: "<1s",
                  label: "Trigger latency",
                  sub: "Deterministic retries",
                },
                {
                  stat: "27 langs",
                  label: "Global by default",
                  sub: "Multi-region routing",
                },
              ].map((item) => (
                <div
                  key={item.stat}
                  className="px-8 py-9 md:py-10 flex flex-col justify-center gap-1.5 bg-transparent hover:bg-secondary/40 transition-colors"
                >
                  <span className="font-display text-2xl md:text-3xl tracking-tight text-foreground">
                    {item.stat}
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {item.label}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {item.sub}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Cell D */}
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            custom={4}
            variants={reveal}
            className="lumina-bento-cell lumina-bento-d rounded-2xl p-8 border border-border bg-background hover:bg-secondary/40 transition-colors group"
          >
            <div className="h-9 w-9 rounded-lg bg-foreground text-primary-foreground flex items-center justify-center">
              <svg
                viewBox="0 0 18 18"
                className="w-4 h-4 fill-none stroke-current"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M4 4h4v4H4zM10 4h4v4h-4zM4 10h4v4H4zM10 10h4v4h-4z" />
              </svg>
            </div>
            <h3 className="mt-5 font-display text-2xl tracking-tight">
              Memory that compounds
            </h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Vector + structured memory keeps agents context-aware across
              millions of interactions.
            </p>
            <div className="mt-6 inline-flex items-center gap-1 text-sm text-foreground opacity-0 group-hover:opacity-100 transition-opacity">
              Learn more
              <svg
                viewBox="0 0 14 14"
                className="w-3.5 h-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M2 7h10M7 2l5 5-5 5" />
              </svg>
            </div>
          </motion.div>

          {/* Cell E */}
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            custom={5}
            variants={reveal}
            className="lumina-bento-cell lumina-bento-e rounded-2xl p-8 border border-border bg-background hover:bg-secondary/40 transition-colors group"
          >
            <div className="h-9 w-9 rounded-lg bg-foreground text-primary-foreground flex items-center justify-center">
              <svg
                viewBox="0 0 18 18"
                className="w-4 h-4 fill-none stroke-current"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <circle cx="9" cy="9" r="7" />
                <path d="M9 5v4l3 2" />
              </svg>
            </div>
            <h3 className="mt-5 font-display text-2xl tracking-tight">
              Real-time triggers
            </h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              React to events from 200+ apps. Sub-second latency, deterministic
              retries, dead-letter queues.
            </p>
            <div className="mt-6 inline-flex items-center gap-1 text-sm text-foreground opacity-0 group-hover:opacity-100 transition-opacity">
              Learn more
              <svg
                viewBox="0 0 14 14"
                className="w-3.5 h-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M2 7h10M7 2l5 5-5 5" />
              </svg>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
