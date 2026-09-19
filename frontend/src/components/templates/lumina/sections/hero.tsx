import * as motion from "motion/react-client";
import { Sparkles, Play } from "lucide-react";
import Navbar from "@/components/templates/lumina/sections/navbar";
import DashboardPreview from "@/components/templates/lumina/sections/dashboard-preview";

const ease = [0.22, 1, 0.36, 1] as const;

export default function Hero() {
  return (
    <section className="relative flex flex-col bg-background overflow-hidden min-h-screen">
      <video
        className="absolute inset-0 w-full h-full object-cover z-0"
        autoPlay
        muted
        loop
        playsInline
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260319_015952_e1deeb12-8fb7-4071-a42a-60779fc64ab6.mp4"
      />
      <div className="absolute inset-0 z-0 bg-gradient-to-b from-white/80 via-white/60 to-white/95 backdrop-blur-[2px]" />

      <div className="relative z-10">
        <Navbar />
      </div>

      <div className="relative z-10 flex flex-col items-center w-full px-6 flex-1 pt-8 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease }}
          className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-background/50 backdrop-blur-md px-4 py-1.5 text-xs font-medium text-foreground mb-8 shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
        >
          <span className="flex h-2 w-2 rounded-full bg-foreground" />
          <span>Now with GPT-5 support</span>
          <Sparkles size={14} className="text-muted-foreground ml-1" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
          className="text-center font-display text-4xl md:text-5xl lg:text-[4rem] leading-[1] tracking-tight text-foreground max-w-[700px]"
        >
          The Future of{" "}
          <em className="italic text-muted-foreground">Smarter</em> Automation.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease }}
          className="mt-6 text-center text-base md:text-xl text-muted-foreground max-w-[550px] leading-relaxed font-medium"
        >
          Automate your busywork with intelligent agents that learn, adapt, and
          execute—so your team can focus on what matters most.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease }}
          className="mt-8 flex items-center gap-4"
        >
          <a
            href="#contact"
            className="rounded-xl px-7 py-3.5 text-sm font-medium bg-foreground text-primary-foreground hover:bg-foreground/90 transition-all shadow-[0_4px_14px_rgba(0,0,0,0.1)] hover:shadow-[0_6px_20px_rgba(0,0,0,0.15)] ring-1 ring-foreground/10"
          >
            Book a demo
          </a>
          <button
            className="h-12 w-12 rounded-xl border border-border/50 bg-background/80 backdrop-blur-sm shadow-sm flex items-center justify-center hover:bg-background transition-colors text-foreground"
            aria-label="Play demo"
          >
            <Play size={16} className="ml-0.5" />
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5, ease }}
          className="mt-16 w-full max-w-5xl"
        >
          <div className="rounded-[20px] overflow-hidden p-2 md:p-3 bg-white/40 border border-white/50 shadow-[var(--shadow-dashboard)] backdrop-blur-xl ring-1 ring-black/5">
            <DashboardPreview />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
