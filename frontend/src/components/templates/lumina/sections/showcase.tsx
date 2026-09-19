import * as motion from "motion/react-client";
import { ArrowRight, ArrowUpRight, Check, MoreHorizontal } from "lucide-react";

type AgentStatus = "running" | "ok" | "warn" | "done";

const STATUS_COLORS: Record<
  AgentStatus,
  { bg: string; text: string; dot: string }
> = {
  running: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  ok: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  warn: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  done: {
    bg: "bg-secondary",
    text: "text-muted-foreground",
    dot: "bg-muted-foreground/50",
  },
};

const AGENTS: {
  status: AgentStatus;
  agent: string;
  action: string;
  when: string;
  badge: string;
}[] = [
  {
    status: "running",
    agent: "Hera",
    action: "Drafting Q3 board report from Notion & HubSpot",
    when: "now",
    badge: "run",
  },
  {
    status: "ok",
    agent: "Atlas",
    action: "Reconciled 142 Stripe invoices · matched 142/142",
    when: "2m",
    badge: "ok",
  },
  {
    status: "warn",
    agent: "Pyra",
    action: "Detected anomaly in expense category 'Travel'",
    when: "6m",
    badge: "warn",
  },
  {
    status: "ok",
    agent: "Odin",
    action: "Sent 38 personalized renewals · 11 replies",
    when: "14m",
    badge: "ok",
  },
  {
    status: "done",
    agent: "Lyra",
    action: "Closed 9 GitHub issues with passing tests",
    when: "22m",
    badge: "done",
  },
  {
    status: "ok",
    agent: "Vega",
    action: "Routed 24 support tickets to specialists",
    when: "31m",
    badge: "ok",
  },
];

function AgentRow({ status, agent, action, when, badge }: (typeof AGENTS)[0]) {
  const c = STATUS_COLORS[status];
  return (
    <div className="grid grid-cols-16 gap-3 items-center px-5 py-3.5 border-b border-border/40 last:border-b-0 text-sm hover:bg-black/[0.01] transition-colors">
      <div className="col-span-1">
        <span className={`inline-flex items-center gap-1.5 ${c.text}`}>
          <span
            className={`h-2 w-2 rounded-full ${c.dot} ${status === "running" ? "lumina-pulse-dot shadow-[0_0_8px_rgba(59,130,246,0.4)]" : "shadow-sm"} ${status === "warn" ? "shadow-[0_0_8px_rgba(245,158,11,0.4)]" : ""} ${status === "ok" ? "shadow-[0_0_8px_rgba(16,185,129,0.4)]" : ""}`}
          />
        </span>
      </div>
      <div className="col-span-2 lg:col-span-3 flex items-center gap-2.5">
        <div className="h-6 w-6 rounded-md bg-foreground text-primary-foreground flex items-center justify-center text-[10px] font-semibold font-display shadow-sm">
          {agent[0]}
        </div>
        <span className="font-semibold tracking-tight text-foreground">
          {agent}
        </span>
      </div>
      <div className="col-span-8 lg:col-span-9 text-muted-foreground truncate font-medium text-[13px]">
        {action}
      </div>
      <div className="col-span-1 hidden lg:block text-xs font-medium text-muted-foreground/60 text-right uppercase tracking-wider">
        {when}
      </div>
      <div className="col-span-3 lg:col-span-2 text-right ml-2">
        <span
          className={`text-[10px] uppercase font-bold tracking-widest ${c.text} ${c.bg} px-2 py-1 rounded-md shadow-sm border border-black/5`}
        >
          {badge}
        </span>
      </div>
    </div>
  );
}

export default function Showcase() {
  return (
    <section className="py-24 md:py-32 px-6 md:px-12 lg:px-20 bg-background">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-14 items-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-secondary/50 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-foreground" />
            Live operations
          </div>
          <h2 className="mt-6 font-display text-4xl md:text-5xl lg:text-[3.5rem] leading-[1] tracking-tight">
            Watch your agents{" "}
            <em className="italic text-muted-foreground">work</em>, in real
            time.
          </h2>
          <p className="mt-5 text-muted-foreground leading-relaxed max-w-md text-lg text-balance">
            A transparent feed of every action your agents take. Filter, drill
            in, and intervene — without breaking the loop.
          </p>
          <ul className="mt-8 space-y-4 text-sm font-medium">
            {[
              "Every tool call & token tracked, with replay",
              "Human-in-the-loop approval gates",
              "Anomaly alerts before incidents become bills",
              "Native integrations with Datadog, Slack & PagerDuty",
            ].map((t) => (
              <li key={t} className="flex items-start gap-3">
                <span className="mt-0.5 h-4 w-4 rounded-full bg-foreground/5 text-foreground flex items-center justify-center shrink-0 ring-1 ring-inset ring-black/5 shadow-sm">
                  <Check size={10} strokeWidth={3} />
                </span>
                <span className="text-foreground/80">{t}</span>
              </li>
            ))}
          </ul>
          <div className="mt-10 flex items-center gap-4">
            <a
              href="#features"
              className="rounded-xl px-6 py-3 text-sm font-semibold bg-white border border-border/80 shadow-sm text-foreground hover:bg-secondary/40 transition-all ring-1 ring-inset ring-black/5"
            >
              Explore the platform
            </a>
            <a
              href="#"
              className="text-sm font-medium text-muted-foreground inline-flex items-center gap-1.5 hover:text-foreground transition-colors group"
            >
              Read the docs{" "}
              <ArrowUpRight
                size={14}
                className="text-muted-foreground/60 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              />
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.5, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="rounded-2xl bg-white overflow-hidden shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-border/80 ring-1 ring-black/[0.02]">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border/60 bg-secondary/20">
              <div className="flex items-center gap-2.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500 lumina-pulse-dot shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                <span className="text-sm font-semibold tracking-tight">
                  Agent activity
                </span>
                <span className="text-[11px] font-medium text-muted-foreground border border-border/60 px-1.5 rounded-sm bg-white">
                  12 active
                </span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                <MoreHorizontal size={16} />
              </div>
            </div>
            <div>
              {AGENTS.map((a, i) => (
                <AgentRow key={i} {...a} />
              ))}
            </div>
            <div className="px-4 py-2.5 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
              <span>Showing 6 of 1,284 events today</span>
              <span className="inline-flex items-center gap-1 text-foreground">
                View timeline <ArrowRight size={12} />
              </span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
