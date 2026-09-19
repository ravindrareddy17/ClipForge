import * as motion from "motion/react-client";
import { Plus } from "lucide-react";

const FAQS = [
  {
    q: "How is Lumina different from Zapier or n8n?",
    a: "Those are deterministic flow tools. Lumina's agents make decisions. They read context, choose the right tool for the situation, retry intelligently, and ask for human input when confidence drops below your threshold.",
  },
  {
    q: "Can I bring my own model?",
    a: "Yes. Use OpenAI, Anthropic, Google, Mistral, or your own self-hosted models. You can mix providers within a single workflow and route by cost, latency, or capability.",
  },
  {
    q: "What about data security?",
    a: "Lumina is SOC 2 Type II and HIPAA-ready. We support customer-managed encryption keys, private VPC deploys, and a strict no-training policy on your data.",
  },
  {
    q: "How does pricing work for usage?",
    a: "You pay per agent run. A run includes all tool calls and tokens consumed within a single triggered action. We give you a soft cap, hard cap, and per-workflow budgets so surprises don't happen.",
  },
  {
    q: "Can I self-host?",
    a: "On the Enterprise plan, yes. We support Kubernetes on AWS, GCP, Azure, and on-prem with air-gapped deploys.",
  },
  {
    q: "Do you offer a free trial?",
    a: "The Starter plan is free forever for up to 1,000 runs per month. Team includes a 14-day trial of unlimited runs.",
  },
];

export default function FAQ() {
  return (
    <section className="py-24 md:py-32 px-6 md:px-12 lg:px-20 bg-background">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="text-center"
        >
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground mx-auto">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            FAQ
          </div>
          <h2 className="mt-5 font-display text-4xl md:text-5xl lg:text-6xl leading-[1] tracking-tight">
            Questions, <em className="italic">answered</em>.
          </h2>
        </motion.div>

        <div className="mt-14 border-t border-border">
          {FAQS.map((f, i) => (
            <motion.details
              key={i}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.4, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
              className="group border-b border-border"
            >
              <summary className="flex items-center justify-between py-6 gap-4 cursor-pointer">
                <span className="font-display text-xl md:text-2xl tracking-tight text-foreground">
                  {f.q}
                </span>
                <span className="h-8 w-8 rounded-full border border-border flex items-center justify-center shrink-0 transition-transform group-open:rotate-45">
                  <Plus size={14} />
                </span>
              </summary>
              <div className="pb-6 pr-12 text-muted-foreground leading-relaxed text-[15px]">
                {f.a}
              </div>
            </motion.details>
          ))}
        </div>
      </div>
    </section>
  );
}
