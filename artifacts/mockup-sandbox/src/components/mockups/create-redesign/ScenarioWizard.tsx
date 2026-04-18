import React, { useState } from "react";
import { 
  ShieldAlert, LayoutDashboard, History, Box, Key, Users, Server, LogOut,
  Search, RotateCcw, ChevronRight, Clock, Tag, Briefcase, Settings2, Sparkles,
  CheckCircle2, Copy, FileText, ArrowRight, AlertCircle, Share2
} from "lucide-react";

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

// --- Layout Components ---
function NavItem({ icon: Icon, label, active, actionIcon: ActionIcon }: { icon: any, label: string, active?: boolean, actionIcon?: any }) {
  return (
    <button className={cn(
      "w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 group",
      active 
        ? "bg-[#ff8c33]/10 text-[#ff8c33]" 
        : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100"
    )}>
      <div className="flex items-center gap-3">
        <Icon className={cn("w-4 h-4", active ? "text-[#ff8c33]" : "text-zinc-500 group-hover:text-zinc-300")} />
        {label}
      </div>
      {ActionIcon && <ActionIcon className="w-3.5 h-3.5 text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity" />}
    </button>
  );
}

// --- Data Models ---
const SCENARIOS = [
  {
    id: "paid",
    title: "Paid Customer",
    description: "Standard 30-day recurring license.",
    icon: Briefcase,
    durationValue: 30,
    durationUnit: "days",
    notePrefix: "Paid: ",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20"
  },
  {
    id: "trial",
    title: "Trial",
    description: "Short 24-hour evaluation access.",
    icon: Clock,
    durationValue: 24,
    durationUnit: "hours",
    notePrefix: "Trial: ",
    color: "text-[#ff8c33]",
    bg: "bg-[#ff8c33]/10",
    border: "border-[#ff8c33]/20"
  },
  {
    id: "internal",
    title: "Internal Test",
    description: "Long-term access for QA and dev.",
    icon: Settings2,
    durationValue: 365,
    durationUnit: "days",
    notePrefix: "Internal: ",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/20"
  },
  {
    id: "promo",
    title: "Promo / Giveaway",
    description: "7-day access for marketing events.",
    icon: Sparkles,
    durationValue: 7,
    durationUnit: "days",
    notePrefix: "Promo: ",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-purple-500/20"
  }
];

export function ScenarioWizard() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  
  // Customization state for Step 2
  const [durationValue, setDurationValue] = useState<number>(30);
  const [durationUnit, setDurationUnit] = useState<string>("days");
  const [note, setNote] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);

  const selectedScenario = SCENARIOS.find(s => s.id === selectedScenarioId);

  const handleSelectScenario = (id: string) => {
    setSelectedScenarioId(id);
    const scenario = SCENARIOS.find(s => s.id === id);
    if (scenario) {
      setDurationValue(scenario.durationValue);
      setDurationUnit(scenario.durationUnit);
      setNote(scenario.notePrefix);
    }
  };

  const handleNext = () => {
    if (step === 1 && selectedScenarioId) {
      setStep(2);
    }
  };

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setStep(3);
    }, 1200);
  };

  const handleReset = () => {
    setStep(1);
    setSelectedScenarioId(null);
    setDurationValue(30);
    setDurationUnit("days");
    setNote("");
  };

  return (
    <div className="flex h-screen w-full bg-[#0a0a0a] text-zinc-300 font-sans selection:bg-[#ff8c33]/30">
      
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-800/50 bg-[#0a0a0a] flex flex-col shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-zinc-800/50">
          <div className="flex items-center gap-2 text-zinc-100 font-medium tracking-tight">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-[#ff8c33] to-[#e66a10] flex items-center justify-center shadow-sm shadow-[#ff8c33]/20">
              <ShieldAlert className="w-3.5 h-3.5 text-white" />
            </div>
            DPRS Admin
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-6 px-3 space-y-8">
          <div className="space-y-1">
            <p className="px-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Overview</p>
            <NavItem icon={LayoutDashboard} label="Dashboard" />
            <NavItem icon={History} label="History" />
            <NavItem icon={Box} label="Builds" />
          </div>

          <div className="space-y-1">
            <p className="px-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Management</p>
            <NavItem icon={Key} label="Create Key" active actionIcon={ChevronRight} />
            <NavItem icon={Users} label="Customers" />
            <NavItem icon={Server} label="Infrastructure" />
          </div>
        </div>

        <div className="p-4 border-t border-zinc-800/50">
          <button className="flex items-center gap-3 px-3 py-2 w-full rounded-md text-sm font-medium text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50 transition-colors">
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#0e0e11]">
        
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-zinc-800/50 bg-[#0e0e11] shrink-0 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-zinc-100 flex items-center gap-3">
              Create Key
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative group">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2 group-focus-within:text-[#ff8c33] transition-colors" />
              <input 
                type="text" 
                placeholder="Search..." 
                className="w-64 bg-zinc-900/50 border border-zinc-800 rounded-md py-1.5 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50 transition-all"
              />
            </div>
          </div>
        </header>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-y-auto p-8 flex items-start justify-center">
          
          <div className="w-full max-w-2xl mt-8">
            {/* Wizard Header */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-zinc-100 mb-2">Issue New License</h2>
              <p className="text-zinc-400 text-sm">Select a scenario to generate a key with sensible defaults.</p>
              
              {/* Stepper */}
              <div className="flex items-center mt-6">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border",
                    step >= 1 ? "bg-[#ff8c33]/10 border-[#ff8c33]/30 text-[#ff8c33]" : "bg-zinc-800 border-zinc-700 text-zinc-500"
                  )}>1</div>
                  <span className={cn("text-sm font-medium", step >= 1 ? "text-zinc-200" : "text-zinc-500")}>Scenario</span>
                </div>
                <div className="w-12 h-px bg-zinc-800 mx-4" />
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border",
                    step >= 2 ? "bg-[#ff8c33]/10 border-[#ff8c33]/30 text-[#ff8c33]" : "bg-zinc-800 border-zinc-700 text-zinc-500"
                  )}>2</div>
                  <span className={cn("text-sm font-medium", step >= 2 ? "text-zinc-200" : "text-zinc-500")}>Review</span>
                </div>
                <div className="w-12 h-px bg-zinc-800 mx-4" />
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border",
                    step >= 3 ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-500" : "bg-zinc-800 border-zinc-700 text-zinc-500"
                  )}>{step === 3 ? <CheckCircle2 className="w-3.5 h-3.5" /> : "3"}</div>
                  <span className={cn("text-sm font-medium", step >= 3 ? "text-zinc-200" : "text-zinc-500")}>Issue</span>
                </div>
              </div>
            </div>

            {/* Wizard Content */}
            <div className="bg-[#0a0a0a] border border-zinc-800/80 rounded-xl shadow-sm overflow-hidden relative min-h-[400px]">
              
              {/* STEP 1: Scenario Selection */}
              {step === 1 && (
                <div className="p-6 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div className="grid grid-cols-2 gap-4">
                    {SCENARIOS.map((scenario) => {
                      const isSelected = selectedScenarioId === scenario.id;
                      return (
                        <label 
                          key={scenario.id}
                          className={cn(
                            "relative flex flex-col p-4 cursor-pointer rounded-lg border-2 transition-all duration-200",
                            isSelected 
                              ? "bg-zinc-900/50 border-[#ff8c33] shadow-[0_0_15px_rgba(255,140,51,0.1)]" 
                              : "bg-zinc-900/20 border-zinc-800/50 hover:bg-zinc-800/40 hover:border-zinc-700"
                          )}
                        >
                          <input 
                            type="radio" 
                            name="scenario" 
                            value={scenario.id} 
                            checked={isSelected}
                            onChange={() => handleSelectScenario(scenario.id)}
                            className="sr-only"
                          />
                          <div className="flex items-center gap-3 mb-2">
                            <div className={cn("p-2 rounded-md border", scenario.bg, scenario.color, scenario.border)}>
                              <scenario.icon className="w-4 h-4" />
                            </div>
                            <span className="font-semibold text-zinc-100">{scenario.title}</span>
                          </div>
                          <p className="text-xs text-zinc-400 leading-relaxed mb-3">
                            {scenario.description}
                          </p>
                          <div className="mt-auto flex items-center gap-2 text-xs font-medium">
                            <span className="bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded">
                              {scenario.durationValue} {scenario.durationUnit}
                            </span>
                          </div>
                          
                          {/* Check Indicator */}
                          <div className={cn(
                            "absolute top-4 right-4 w-4 h-4 rounded-full border flex items-center justify-center transition-colors",
                            isSelected ? "border-[#ff8c33] bg-[#ff8c33]" : "border-zinc-700 bg-zinc-900"
                          )}>
                            {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-[#0a0a0a]" />}
                          </div>
                        </label>
                      );
                    })}
                  </div>

                  <div className="mt-8 flex justify-end">
                    <button 
                      onClick={handleNext}
                      disabled={!selectedScenarioId}
                      className="flex items-center gap-2 px-5 py-2.5 bg-[#ff8c33] hover:bg-[#ff9d4d] disabled:opacity-50 disabled:hover:bg-[#ff8c33] disabled:cursor-not-allowed text-orange-950 rounded-md text-sm font-semibold shadow-sm transition-all"
                    >
                      Continue
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 2: Review & Customize */}
              {step === 2 && (
                <div className="flex flex-col h-full animate-in fade-in slide-in-from-right-4 duration-300">
                  <div className="p-6 flex-1">
                    
                    <div className="flex items-center gap-3 mb-6 p-4 rounded-lg bg-zinc-900 border border-zinc-800">
                      <div className={cn("p-2 rounded-md border", selectedScenario?.bg, selectedScenario?.color, selectedScenario?.border)}>
                        {selectedScenario && <selectedScenario.icon className="w-5 h-5" />}
                      </div>
                      <div>
                        <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-0.5">Selected Scenario</p>
                        <p className="text-sm font-semibold text-zinc-100">{selectedScenario?.title}</p>
                      </div>
                      <button 
                        onClick={() => setStep(1)}
                        className="ml-auto text-xs font-medium text-zinc-400 hover:text-zinc-200 underline underline-offset-2"
                      >
                        Change
                      </button>
                    </div>

                    <div className="space-y-5">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label className="text-xs font-semibold text-zinc-400">Duration</label>
                          <div className="flex rounded-md shadow-sm">
                            <input 
                              type="number" 
                              value={durationValue}
                              onChange={(e) => setDurationValue(parseInt(e.target.value) || 0)}
                              className="w-full bg-zinc-900 border border-zinc-800 border-r-0 rounded-l-md py-2 px-3 text-sm text-zinc-100 focus:outline-none focus:border-[#ff8c33]/50 focus:ring-1 focus:ring-[#ff8c33]/50 z-10"
                            />
                            <select 
                              value={durationUnit}
                              onChange={(e) => setDurationUnit(e.target.value)}
                              className="bg-zinc-800 border border-zinc-700 rounded-r-md py-2 px-3 text-sm text-zinc-300 font-medium focus:outline-none focus:border-[#ff8c33]/50 focus:ring-1 focus:ring-[#ff8c33]/50"
                            >
                              <option value="minutes">Minutes</option>
                              <option value="hours">Hours</option>
                              <option value="days">Days</option>
                            </select>
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
                            Note <span className="text-zinc-600 font-normal">(Optional)</span>
                          </label>
                          <input 
                            type="text" 
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                            placeholder="e.g. Customer Name..."
                            className="w-full bg-zinc-900 border border-zinc-800 rounded-md py-2 px-3 text-sm text-zinc-100 focus:outline-none focus:border-[#ff8c33]/50 focus:ring-1 focus:ring-[#ff8c33]/50"
                          />
                        </div>
                      </div>

                      <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 flex gap-3 text-amber-500">
                        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                        <div className="text-xs leading-relaxed">
                          This license will be immediately active upon generation. It will expire exactly {durationValue} {durationUnit} from now unless suspended.
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-6 border-t border-zinc-800/80 bg-zinc-900/30 flex justify-between items-center mt-auto">
                    <button 
                      onClick={() => setStep(1)}
                      className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
                    >
                      Back
                    </button>
                    <button 
                      onClick={handleGenerate}
                      disabled={isGenerating}
                      className="flex items-center gap-2 px-6 py-2.5 bg-[#ff8c33] hover:bg-[#ff9d4d] disabled:opacity-80 text-orange-950 rounded-md text-sm font-semibold shadow-[0_0_15px_rgba(255,140,51,0.2)] transition-all relative overflow-hidden"
                    >
                      {isGenerating ? (
                        <>
                          <div className="w-4 h-4 border-2 border-orange-950/30 border-t-orange-950 rounded-full animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          Generate License
                          <Key className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 3: Success State */}
              {step === 3 && (
                <div className="p-8 flex flex-col items-center justify-center text-center h-full animate-in zoom-in-95 duration-500">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(52,211,153,0.15)] border border-emerald-500/20">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                  </div>
                  
                  <h3 className="text-xl font-semibold text-zinc-100 mb-2">License Generated</h3>
                  <p className="text-sm text-zinc-400 mb-8 max-w-sm">
                    The {selectedScenario?.title.toLowerCase()} license has been securely generated and is ready to use.
                  </p>

                  <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-lg p-5 mb-8 relative group">
                    <div className="absolute -top-3 left-4 bg-[#0a0a0a] px-2 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                      License Key
                    </div>
                    <code className="block text-xl md:text-2xl font-mono text-zinc-200 font-medium tracking-wider mb-4">
                      A1B2-C3D4-E5F6-G7H8
                    </code>
                    
                    <div className="flex items-center gap-3">
                      <button className="flex-1 flex items-center justify-center gap-2 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md text-sm font-medium transition-colors border border-zinc-700">
                        <Copy className="w-4 h-4 text-zinc-400" />
                        Copy Key
                      </button>
                      <button className="flex-1 flex items-center justify-center gap-2 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md text-sm font-medium transition-colors border border-zinc-700">
                        <Share2 className="w-4 h-4 text-zinc-400" />
                        Share
                      </button>
                    </div>
                  </div>

                  {/* Audit Entry Preview */}
                  <div className="w-full max-w-md flex items-center gap-3 text-left p-3 rounded-md bg-zinc-900/50 border border-zinc-800/50 mb-8">
                    <FileText className="w-4 h-4 text-zinc-500 shrink-0" />
                    <div className="flex-1 min-w-0 text-xs">
                      <div className="flex justify-between mb-0.5">
                        <span className="text-zinc-300 font-medium">System Log</span>
                        <span className="text-zinc-500">Just now</span>
                      </div>
                      <p className="text-zinc-400 truncate">
                        Generated {durationValue}-{durationUnit} key. Note: "{note}"
                      </p>
                    </div>
                  </div>

                  <button 
                    onClick={handleReset}
                    className="text-sm font-medium text-zinc-400 hover:text-zinc-200 underline underline-offset-4"
                  >
                    Create another key
                  </button>
                </div>
              )}

            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
