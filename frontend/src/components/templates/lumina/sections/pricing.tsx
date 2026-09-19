import * as motion from "motion/react-client";
import { Check } from "lucide-react";

const PRICING = [
  {
    name: "Starter",
    price: "$0",
    period: "/mo",
    blurb: "For builders & curious teams getting hands-on.",
    cta: "Start free",
    features: [
      "Up to 3 agents",
      "1,000 runs / mo",
      "Core integrations",
      "Community support",
    ],
    popular: false,
  },
  {
    name: "Team",
    price: "$59",
    period: "/seat / mo",
    blurb: "For teams shipping agents to real users.",
    cta: "Start 14-day trial",
    features: [
      "Unlimited agents",
      "250,000 runs / mo",
      "All integrations + bring-your-own",
      "RBAC, SSO, audit logs",
      "Priority email support",
    ],
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    blurb: "For regulated, global, & high-volume deployments.",
    cta: "Talk to sales",
    features: [
      "Volume pricing",
      "On-prem / VPC deploy",
      "HIPAA, FedRAMP, custom DPA",
      "Dedicated solutions engineer",
      "99.99% uptime SLA",
    ],
    popular: false,
  },
];

export default function Pricing() {
  return (
    <section
      id="pricing"
      className="py-24 md:py-32 px-6 md:px-12 lg:px-20 bg-secondary/40"
    >
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-2xl mx-auto text-center"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-background px-3 py-1 text-xs font-medium text-muted-foreground mx-auto shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-foreground" />
            Pricing
          </div>
          <h2 className="mt-6 font-display text-4xl md:text-5xl lg:text-[3.5rem] leading-[1] tracking-tight">
            Simple pricing.{" "}
            <em className="italic text-muted-foreground">Honest</em> usage.
          </h2>
          <p className="mt-5 text-muted-foreground text-lg md:text-xl max-w-[500px] mx-auto font-medium text-balance">
            Pay for the work your agents do, not the seats they sit in. Stop any
            time.
          </p>
        </motion.div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          {PRICING.map((p, i) => (
            <motion.div
              key={p.name}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{
                duration: 0.5,
                delay: i * 0.08,
                ease: [0.22, 1, 0.36, 1],
              }}
              className={
                "rounded-3xl p-8 border flex flex-col transition-all " +
                (p.popular
                  ? "bg-foreground text-primary-foreground border-foreground shadow-[0_12px_40px_-12px_rgba(0,0,0,0.1),0_0_0_1px_rgba(0,0,0,0.04)] ring-1 ring-black/5"
                  : "bg-white border-border/80 shadow-sm")
              }
            >
              <div className="flex items-center justify-between">
                <h3 className="font-display text-2xl tracking-tight">
                  {p.name}
                </h3>
                {p.popular && (
                  <span className="text-[10px] uppercase font-bold tracking-wider bg-white/10 text-primary-foreground rounded-md px-2.5 py-1">
                    Most popular
                  </span>
                )}
              </div>
              <p
                className={`mt-3 text-sm leading-relaxed ${p.popular ? "text-primary-foreground/70" : "text-muted-foreground"}`}
              >
                {p.blurb}
              </p>
              <div className="mt-8 flex items-baseline gap-1.5">
                <span className="font-display text-5xl tracking-tighter">
                  {p.price}
                </span>
                <span
                  className={`text-sm font-medium ${p.popular ? "text-primary-foreground/60" : "text-muted-foreground"}`}
                >
                  {p.period}
                </span>
              </div>
              <hr
                className={`my-8 ${p.popular ? "border-primary-foreground/10" : "border-border"}`}
              />
              <ul className="space-y-4 text-sm flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-3">
                    <span
                      className={
                        "mt-0.5 h-5 w-5 rounded-full flex items-center justify-center shrink-0 shadow-sm " +
                        (p.popular
                          ? "bg-white/10 text-primary-foreground"
                          : "bg-foreground/5 text-foreground")
                      }
                    >
                      <Check size={10} strokeWidth={3} />
                    </span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <a
                href="#contact"
                className={
                  "mt-10 rounded-xl py-3.5 text-[15px] font-semibold text-center transition-all block shadow-sm " +
                  (p.popular
                    ? "bg-white text-foreground hover:bg-white/90 ring-1 ring-inset ring-black/5"
                    : "bg-foreground text-primary-foreground hover:bg-foreground/90 ring-1 ring-inset ring-black/10")
                }
              >
                {p.cta}
              </a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
