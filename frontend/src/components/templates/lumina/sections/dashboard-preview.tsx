import {
  Home,
  CheckSquare,
  ArrowLeftRight,
  Wallet,
  CreditCard,
  TrendingUp,
  Building2,
  Workflow,
  Bell,
  Settings,
  ChevronDown,
  Search,
  Plus,
  MoreHorizontal,
  Check,
} from "lucide-react";

function SidebarItem({
  icon: Icon,
  label,
  active,
  badge,
  chev,
}: {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  badge?: string;
  chev?: boolean;
}) {
  return (
    <div
      className={
        "flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-default " +
        (active
          ? "bg-white text-foreground shadow-[0_1px_3px_rgba(0,0,0,0.05)] ring-1 ring-black/[0.03]"
          : "text-muted-foreground hover:bg-black/[0.02] hover:text-foreground")
      }
    >
      <div className="flex items-center gap-2.5">
        <Icon
          size={14}
          className={active ? "text-foreground" : "text-muted-foreground/70"}
        />
        <span>{label}</span>
      </div>
      <div className="flex items-center gap-1">
        {badge && (
          <span className="text-[10px] bg-foreground/5 text-foreground font-semibold rounded-md px-1.5 py-0.5 tracking-tight">
            {badge}
          </span>
        )}
        {chev && <ChevronDown size={10} className="text-muted-foreground/70" />}
      </div>
    </div>
  );
}

function ActionPill({
  children,
  accent,
}: {
  children: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <button
      className={
        "rounded-md px-3.5 py-1.5 text-[10.5px] font-semibold whitespace-nowrap transition-all " +
        (accent
          ? "bg-foreground text-primary-foreground shadow-[0_2px_8px_rgba(0,0,0,0.12)]"
          : "bg-white border border-border text-foreground hover:bg-secondary/80 shadow-[0_1px_2px_rgba(0,0,0,0.02)]")
      }
    >
      {children}
    </button>
  );
}

function BalanceChart() {
  return (
    <svg
      viewBox="0 0 320 80"
      className="h-20 w-full"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="lm-balanceFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(239 84% 67%)" stopOpacity="0.15" />
          <stop offset="100%" stopColor="hsl(239 84% 67%)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M0,55 C25,52 40,42 65,40 C90,38 105,55 130,52 C155,49 170,28 200,30 C230,32 245,46 275,38 C295,33 310,22 320,18 L320,80 L0,80 Z"
        fill="url(#lm-balanceFill)"
      />
      <path
        d="M0,55 C25,52 40,42 65,40 C90,38 105,55 130,52 C155,49 170,28 200,30 C230,32 245,46 275,38 C295,33 310,22 320,18"
        fill="none"
        stroke="hsl(239 84% 67%)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="320" cy="18" r="2.5" fill="hsl(239 84% 67%)" />
    </svg>
  );
}

function TxRow({
  date,
  desc,
  amount,
  status,
  statusBg,
  statusFg,
}: {
  date: string;
  desc: string;
  amount: string;
  status: string;
  statusBg: string;
  statusFg: string;
}) {
  return (
    <tr className="text-[10px]">
      <td className="py-2 text-muted-foreground">{date}</td>
      <td className="py-2 text-foreground">{desc}</td>
      <td
        className={
          "py-2 tabular-nums font-medium " +
          (amount.startsWith("+") ? "text-emerald-600" : "text-foreground")
        }
      >
        {amount}
      </td>
      <td className="py-2">
        <span
          className="inline-flex items-center gap-1 rounded-full px-1.5 py-[1px] text-[9px]"
          style={{ background: statusBg, color: statusFg }}
        >
          <span
            className="h-1 w-1 rounded-full"
            style={{ background: statusFg }}
          />
          {status}
        </span>
      </td>
    </tr>
  );
}

export default function DashboardPreview() {
  return (
    <div className="rounded-xl overflow-hidden bg-background text-foreground shrink-0 select-none pointer-events-none shadow-[0_2px_40px_-8px_rgba(0,0,0,0.05)] border border-border/80 ring-1 ring-black/[0.02]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-3 md:px-4 py-2 border-b border-border bg-white h-11">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded-[5px] bg-foreground text-primary-foreground flex items-center justify-center text-[10px] font-semibold font-display shadow-sm">
            L
          </div>
          <span className="text-[12px] font-semibold tracking-tight">
            Lumina
          </span>
          <ChevronDown size={11} className="text-muted-foreground/80 mt-0.5" />
        </div>
        <div className="hidden sm:flex items-center gap-2 px-2.5 h-7 rounded-md bg-secondary/80 w-64 max-w-[40%] ring-1 ring-inset ring-black/5">
          <Search size={12} className="text-muted-foreground/70" />
          <span className="text-[11px] text-muted-foreground/80 flex-1 font-medium">
            Search…
          </span>
          <span className="text-[9px] text-muted-foreground/70 border border-border bg-background rounded-[3px] px-1.5 py-0.5 tracking-tighter">
            ⌘K
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button className="rounded-md bg-foreground text-primary-foreground text-[10.5px] px-3 py-1 font-medium shadow-sm active:scale-95 transition-transform">
            New Agent
          </button>
          <Bell size={13} className="text-muted-foreground/80" />
          <div className="h-6 w-6 rounded-full bg-foreground/5 text-foreground flex items-center justify-center text-[9px] font-semibold ring-1 ring-inset ring-black/10">
            JB
          </div>
        </div>
      </div>

      <div className="flex min-h-[360px] bg-secondary/20">
        {/* Sidebar */}
        <aside className="hidden md:flex w-[180px] shrink-0 p-2.5 border-r border-border bg-white/50 flex-col justify-between">
          <div>
            <div className="space-y-0.5">
              <SidebarItem icon={Home} label="Home" active />
              <SidebarItem icon={CheckSquare} label="Tasks" badge="10" />
              <SidebarItem icon={ArrowLeftRight} label="Activity" />
              <SidebarItem icon={Wallet} label="Workflows" chev />
              <SidebarItem icon={CreditCard} label="Agents" />
              <SidebarItem icon={TrendingUp} label="Analytics" />
              <SidebarItem icon={Building2} label="Integrations" chev />
            </div>
            <div className="mt-4 mb-2 px-2.5 text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/60">
              Automations
            </div>
            <div className="space-y-0.5">
              <SidebarItem icon={Workflow} label="Trade routes" />
              <SidebarItem icon={Wallet} label="Payments" />
              <SidebarItem icon={Bell} label="Alerts" />
            </div>
          </div>
          <div className="space-y-0.5 pt-4 border-t border-border">
            <SidebarItem icon={Settings} label="Settings" />
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 p-3 md:p-5">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold tracking-tight">
              Welcome, Jane
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
              <span className="lumina-pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
              All systems online
            </div>
          </div>

          {/* Action pills */}
          <div className="mt-2.5 flex items-center gap-1.5 overflow-x-auto">
            <ActionPill accent>Deploy</ActionPill>
            <ActionPill>Monitor</ActionPill>
            <ActionPill>Schedule</ActionPill>
            <ActionPill>Integrate</ActionPill>
            <ActionPill>Alert</ActionPill>
            <ActionPill>Review</ActionPill>
            <span className="text-[10px] text-muted-foreground px-1">
              + Customize
            </span>
          </div>

          {/* Two cards */}
          <div className="mt-3 flex gap-3">
            {/* Balance */}
            <div className="flex-1 basis-0 rounded-lg bg-white border border-border p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground">
                    Agent Performance
                  </span>
                  <span className="h-3 w-3 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                    <Check size={8} strokeWidth={3} />
                  </span>
                </div>
                <MoreHorizontal size={12} className="text-muted-foreground" />
              </div>
              <div className="mt-1 flex items-baseline gap-0.5">
                <span className="text-base font-semibold tabular-nums">
                  3.8M
                </span>
                <span className="text-xs text-muted-foreground">runs/wk</span>
              </div>
              <div className="mt-2 flex items-center gap-3 text-[9px] text-muted-foreground">
                <span>Last 30 Days</span>
                <span className="text-emerald-600 font-medium">+18.4%</span>
                <span className="text-rose-500 font-medium">0.01% fail</span>
              </div>
              <div className="mt-1">
                <BalanceChart />
              </div>
            </div>

            {/* Accounts */}
            <div className="flex-1 basis-0 rounded-lg bg-white border border-border p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold">Active Agents</span>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Plus size={11} />
                  <MoreHorizontal size={12} />
                </div>
              </div>
              <div className="mt-1">
                {[
                  { name: "Hera", amount: "Drafting Q3 report" },
                  { name: "Atlas", amount: "Reconciling invoices" },
                  { name: "Pyra", amount: "Expense anomaly scan" },
                ].map((a) => (
                  <div
                    key={a.name}
                    className="py-3 flex items-center justify-between text-[11px] border-b border-border last:border-b-0"
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-5 w-5 rounded-md bg-foreground text-primary-foreground flex items-center justify-center text-[9px] font-semibold font-display">
                        {a.name[0]}
                      </div>
                      <span>{a.name}</span>
                    </div>
                    <span className="tabular-nums text-muted-foreground">
                      {a.amount}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Activity log */}
          <div className="mt-3 rounded-lg bg-white border border-border p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold">Recent Activity</span>
              <span className="text-[10px] text-muted-foreground">
                View all
              </span>
            </div>
            <table className="w-full mt-1.5">
              <thead>
                <tr className="text-[9px] uppercase tracking-wider text-muted-foreground text-left">
                  <th className="font-medium pb-1">Time</th>
                  <th className="font-medium pb-1">Agent</th>
                  <th className="font-medium pb-1">Runs</th>
                  <th className="font-medium pb-1">Status</th>
                </tr>
              </thead>
              <tbody>
                <TxRow
                  date="now"
                  desc="Hera"
                  amount="+142"
                  status="Running"
                  statusBg="#DBEAFE"
                  statusFg="#1D4ED8"
                />
                <TxRow
                  date="2m"
                  desc="Atlas"
                  amount="+38"
                  status="Done"
                  statusBg="#DCFCE7"
                  statusFg="#15803D"
                />
                <TxRow
                  date="6m"
                  desc="Pyra"
                  amount="+1"
                  status="Warning"
                  statusBg="#FEF3C7"
                  statusFg="#B45309"
                />
                <TxRow
                  date="14m"
                  desc="Odin"
                  amount="+11"
                  status="Done"
                  statusBg="#DCFCE7"
                  statusFg="#15803D"
                />
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </div>
  );
}
