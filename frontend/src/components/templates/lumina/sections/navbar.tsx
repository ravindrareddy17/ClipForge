export default function Navbar() {
  return (
    <nav className="relative z-20 flex items-center justify-between px-6 md:px-12 lg:px-20 py-5 font-sans">
      <a
        href="#"
        className="text-xl font-semibold tracking-tight flex items-center gap-1"
      >
        <span className="font-display text-2xl leading-none">✦</span>
        <span>Lumina</span>
      </a>
      <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
        <a href="#features" className="hover:text-foreground transition-colors">
          Home
        </a>
        <a href="#pricing" className="hover:text-foreground transition-colors">
          Pricing
        </a>
        <a href="#about" className="hover:text-foreground transition-colors">
          About
        </a>
        <a href="#contact" className="hover:text-foreground transition-colors">
          Contact
        </a>
      </div>
      <a
        href="#contact"
        className="rounded-xl px-5 py-2.5 text-sm font-medium bg-foreground text-primary-foreground hover:bg-foreground/90 transition-all shadow-[0_2px_8px_rgba(0,0,0,0.08)]"
      >
        Book a demo
      </a>
    </nav>
  );
}
