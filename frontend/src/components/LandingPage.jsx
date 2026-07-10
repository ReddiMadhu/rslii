import React from 'react';
import { Zap, GitBranch, Columns3, Code, Database, ArrowRight, Upload, Search, BarChart3, Box } from 'lucide-react';
import useAnalysisStore, { APP_STATES } from '../store/useAnalysisStore';

function LandingPage({ themeToggle }) {
  const setAppState = useAnalysisStore((s) => s.setAppState);

  const handlePythonClick = () => {
    setAppState(APP_STATES.UPLOAD_SCRIPT);
  };

  const handleAlteryxClick = () => {
    // Kept open but no functional backend yet
    console.log("Alteryx Flow Selected");
  };

  const scrollToPlatforms = () => {
    const el = document.getElementById("platform-select");
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-primary)] overflow-hidden animate-fade-in">
      {/* Background glowing orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-[var(--primary)] opacity-[0.08] blur-[120px] pointer-events-none mix-blend-screen" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] rounded-full bg-[var(--node-source)] opacity-[0.05] blur-[100px] pointer-events-none mix-blend-screen" />

      {/* Navigation */}
      <header className="flex items-center justify-between px-8 py-5 z-10">
        <div className="flex items-center gap-3">
          <img src="/etlpulse_ai_logo.svg" alt="ETLPulse.AI" className="h-10 w-auto" />
        </div>
        <div>
          {themeToggle}
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center w-full z-10 px-6">
        
        {/* Hero Section */}
        <section className="flex flex-col items-center justify-center text-center max-w-4xl mx-auto pt-20 pb-24">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[var(--bg-card)] mb-8 shadow-sm">
            <span className="flex h-2 w-2 rounded-full bg-[var(--primary)] animate-pulse" />
            <span className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">The Intelligent Data Lineage Platform</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-[var(--text-primary)] leading-[1.1] mb-6">
            Intelligent visibility into every <span className="gradient-text">data transformation.</span>
          </h1>
          <p className="text-lg md:text-xl text-[var(--text-secondary)] max-w-2xl mx-auto mb-10 leading-relaxed">
            Upload your ETL script and instantly map column-level lineage, enrich context with AI, and track every data movement across your pipeline.
          </p>
          <button 
            onClick={scrollToPlatforms}
            className="group relative flex items-center gap-3 px-8 py-4 rounded-full font-bold text-white transition-all duration-300 hover:scale-105 overflow-hidden shadow-[0_0_40px_rgba(251,78,11,0.4)] bg-gradient-to-br from-[var(--primary)] to-[var(--primary-dark)]"
          >
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
            Get Started
            <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </section>

        {/* How It Works */}
        <section className="w-full max-w-6xl mx-auto py-20 border-t border-[var(--border)]">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-4">How it works</h2>
            <p className="text-[var(--text-secondary)]">From raw script to interactive map in seconds.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            <div className="hidden md:block absolute top-[40px] left-[15%] right-[15%] h-[2px] bg-gradient-to-r from-[var(--border)] via-[var(--primary)] to-[var(--border)] opacity-20" />
            
            <div className="flex flex-col items-center text-center z-10">
              <div className="w-20 h-20 rounded-2xl glass flex items-center justify-center mb-6 shadow-lg text-[var(--primary)]">
                <Upload size={32} />
              </div>
              <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">1. Upload Script</h3>
              <p className="text-[var(--text-muted)] text-sm px-4">Drop your Python ETL scripts directly into the analyzer.</p>
            </div>
            
            <div className="flex flex-col items-center text-center z-10">
              <div className="w-20 h-20 rounded-2xl glass flex items-center justify-center mb-6 shadow-lg text-[var(--node-source)]">
                <Search size={32} />
              </div>
              <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">2. Instant Parse</h3>
              <p className="text-[var(--text-muted)] text-sm px-4">Our AST engine safely extracts operations without executing code.</p>
            </div>
            
            <div className="flex flex-col items-center text-center z-10">
              <div className="w-20 h-20 rounded-2xl glass flex items-center justify-center mb-6 shadow-lg text-[var(--node-target)]">
                <BarChart3 size={32} />
              </div>
              <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">3. Visualize</h3>
              <p className="text-[var(--text-muted)] text-sm px-4">Explore interactive graphs and AI-enriched summaries.</p>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="w-full max-w-6xl mx-auto py-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass glass-hover p-8 rounded-2xl flex flex-col gap-4 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-center text-[var(--node-source)] mb-2">
                <GitBranch size={24} />
              </div>
              <h3 className="text-lg font-bold text-[var(--text-primary)] leading-tight">Know exactly where your data goes</h3>
              <p className="text-[var(--text-muted)] text-sm">Automated AST lineage mapping exposes every node and connection across your pipeline.</p>
            </div>
            
            <div className="glass glass-hover p-8 rounded-2xl flex flex-col gap-4 transition-all duration-300 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--primary)] opacity-[0.05] blur-[40px] rounded-full" />
              <div className="w-12 h-12 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-center text-[var(--primary)] mb-2">
                <Zap size={24} />
              </div>
              <h3 className="text-lg font-bold text-[var(--text-primary)] leading-tight">Understand complex code instantly</h3>
              <p className="text-[var(--text-muted)] text-sm">AI-powered context enrichment translates complex transformations into plain English.</p>
            </div>
            
            <div className="glass glass-hover p-8 rounded-2xl flex flex-col gap-4 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-center text-[var(--node-target)] mb-2">
                <Columns3 size={24} />
              </div>
              <h3 className="text-lg font-bold text-[var(--text-primary)] leading-tight">Pinpoint column-level changes</h3>
              <p className="text-[var(--text-muted)] text-sm">Granular tracking reveals precisely when columns are added, renamed, or modified.</p>
            </div>
          </div>
        </section>

        {/* Platform Selection */}
        <section id="platform-select" className="w-full max-w-4xl mx-auto py-24 mb-16">
          <div className="glass p-10 md:p-14 rounded-[2rem] border-[var(--border)] shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-b from-[var(--bg-glass)] to-[var(--bg-card)] pointer-events-none" />
            <div className="relative z-10 flex flex-col items-center text-center">
              <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-4">Select your ETL Platform</h2>
              <p className="text-[var(--text-secondary)] mb-10 max-w-md">Choose your source to begin the analysis process.</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                {/* Python Script Card */}
                <button 
                  onClick={handlePythonClick}
                  className="group relative flex flex-col items-center justify-center gap-4 p-8 rounded-2xl bg-[var(--bg-card)] border-2 border-[var(--border)] hover:border-[var(--primary)] transition-all duration-300 hover:shadow-[0_10px_40px_rgba(251,78,11,0.15)] hover:-translate-y-1 text-left w-full overflow-hidden"
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-[var(--primary)] opacity-0 group-hover:opacity-[0.05] blur-[20px] rounded-full transition-opacity duration-500" />
                  <div className="w-16 h-16 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Code size={32} className="text-[var(--text-primary)] group-hover:text-[var(--primary)] transition-colors duration-300" />
                  </div>
                  <div className="text-center">
                    <h3 className="text-xl font-bold text-[var(--text-primary)] mb-1">Python Script</h3>
                    <p className="text-sm text-[var(--text-muted)]">.py files using Pandas</p>
                  </div>
                </button>

                {/* Alteryx Flow Card */}
                <button 
                  onClick={handleAlteryxClick}
                  className="group relative flex flex-col items-center justify-center gap-4 p-8 rounded-2xl bg-[var(--bg-card)] border-2 border-[var(--border)] hover:border-[var(--border-hover)] transition-all duration-300 hover:shadow-xl hover:-translate-y-1 text-left w-full overflow-hidden"
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-[var(--node-source)] opacity-0 group-hover:opacity-[0.05] blur-[20px] rounded-full transition-opacity duration-500" />
                  <div className="w-16 h-16 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Box size={32} className="text-[var(--text-primary)] group-hover:text-[var(--node-source)] transition-colors duration-300" />
                  </div>
                  <div className="text-center">
                    <h3 className="text-xl font-bold text-[var(--text-primary)] mb-1">Alteryx Flow</h3>
                    <p className="text-sm text-[var(--text-muted)]">.yxmd workflows</p>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="py-8 text-center border-t border-[var(--border)] bg-[var(--bg-card)] z-10">
        <p className="text-[var(--text-muted)] text-sm">
          &copy; {new Date().getFullYear()} ETLPulse.AI. Intelligent visibility across data transformations.
        </p>
      </footer>
    </div>
  );
}

export default LandingPage;
