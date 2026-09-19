function XIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4l16 16M20 4L4 20" />
    </svg>
  );
}

function LinkedinIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z" />
      <rect x="2" y="9" width="4" height="12" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

function GithubIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
    </svg>
  );
}

function SlackIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <rect x="13" y="2" width="3" height="8" rx="1.5" />
      <rect x="8" y="14" width="3" height="8" rx="1.5" />
      <rect x="2" y="8" width="8" height="3" rx="1.5" />
      <rect x="14" y="13" width="8" height="3" rx="1.5" />
    </svg>
  );
}

const FOOTER_COLS = [
  { title: "Product", links: ["Platform", "Agents", "Integrations", "Changelog", "Roadmap"] },
  { title: "Company", links: ["About", "Customers", "Careers", "Press", "Contact"] },
  { title: "Resources", links: ["Documentation", "API reference", "Guides", "Community", "Status"] },
  { title: "Legal", links: ["Privacy", "Terms", "Security", "DPA", "Subprocessors"] },
];

export default function Footer() {
  return (
    <footer id="about" className="px-6 md:px-12 lg:px-20 pb-10 bg-background border-t border-border pt-16">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-10">
          <div className="col-span-2 max-w-sm">
            <a href="#" className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-1">
              <span className="font-display text-2xl leading-none">✦</span>
              <span>Lumina</span>
            </a>
            <p className="mt-4 text-sm text-muted-foreground leading-relaxed">
              The platform for intelligent automation. Build, deploy, and govern agents your business can trust.
            </p>
            <div className="mt-6 flex items-center gap-3 text-muted-foreground">
              <a href="#" className="hover:text-foreground transition-colors"><XIcon size={16} /></a>
              <a href="#" className="hover:text-foreground transition-colors"><LinkedinIcon size={16} /></a>
              <a href="#" className="hover:text-foreground transition-colors"><GithubIcon size={16} /></a>
              <a href="#" className="hover:text-foreground transition-colors"><SlackIcon size={16} /></a>
            </div>
          </div>
          {FOOTER_COLS.map((col) => (
            <div key={col.title}>
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground">{col.title}</h4>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l}>
                    <a href="#" className="text-sm text-foreground hover:text-accent transition-colors">
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-6 border-t border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs text-muted-foreground">
          <span>© {new Date().getFullYear()} Lumina Labs, Inc. All rights reserved.</span>
          <div className="flex items-center gap-5">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 lumina-pulse-dot" />
              All systems normal
            </span>
            <span>Built in San Francisco · Berlin · Tokyo</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
