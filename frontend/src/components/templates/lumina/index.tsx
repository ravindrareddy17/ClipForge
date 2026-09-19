import Hero from "./sections/hero";
import LogoStrip from "./sections/logo-strip";
import Features from "./sections/features";
import Workflow from "./sections/workflow";
import Showcase from "./sections/showcase";
import Stats from "./sections/stats";
import Testimonials from "./sections/testimonials";
import Pricing from "./sections/pricing";
import FAQ from "./sections/faq";
import FinalCTA from "./sections/cta";
import Footer from "./sections/footer";

export default function Lumina() {
  return (
    <main className="min-h-screen bg-background text-foreground selection:bg-foreground selection:text-background">
      <Hero />
      <LogoStrip />
      <Features />
      <Workflow />
      <Showcase />
      <Stats />
      <Testimonials />
      <Pricing />
      <FAQ />
      <FinalCTA />
      <Footer />
    </main>
  );
}
