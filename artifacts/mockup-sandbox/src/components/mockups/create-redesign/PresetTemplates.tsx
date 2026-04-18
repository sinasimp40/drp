import React, { useState } from "react";
import { 
  ShieldAlert, Key, LayoutDashboard, History, Box, LogOut, 
  Users, Server, Search, CheckCircle2, ChevronRight, Copy, 
  Mail, QrCode, ArrowRight, Sparkles, Clock, CalendarDays, Plus
} from "lucide-react";

// --- UI Components Inline ---

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

const Badge = ({ children, variant = "default", className }: { children: React.ReactNode, variant?: "default" | "success" | "warning" | "danger" | "neutral", className?: string }) => {
  const variants = {
    default: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    success: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    danger: "bg-rose-500/10 text-rose-500 border-rose-500/20",
    neutral: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border", variants[variant], className)}>
      {children}
    </span>
  );
};

// --- Mock Data & Constants ---

const PRESETS = [
  { id: "1h", label: "1 Hour", desc: "Trial / testing", icon: Clock },
  { id: "24h", label: "24 Hours", desc: "Day pass", icon: Clock, badge: "Most used" },
  { id: "7d", label: "7 Days", desc: "Weekly license", icon: CalendarDays },
  { id: "30d", label: "30 Days", desc: "Monthly license", icon: CalendarDays },
  { id: "custom", label: "Custom", desc: "Specific duration", icon: Plus },
];

export function PresetTemplates() {
  const [selectedPreset, setSelectedPreset] = useState("24h");
  const [note, setNote] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setGeneratedKey("DPRS-A1B2-C3D4-E5F6");
    }, 1200);
  };

  const handleCopy = () => {
    if (generatedKey) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleReset = () => {
    setGeneratedKey(null);
    setNote("");
    setSelectedPreset("24h");
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
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#0e0e11] relative">
        {/* Background glow for ambient effect */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[#ff8c33]/5 blur-[120px] rounded-full pointer-events-none" />

        {/* Header */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-zinc-800/50 bg-[#0e0e11]/80 backdrop-blur-sm shrink-0 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-zinc-100 flex items-center gap-3">
              Issue License Key
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
        <div className="flex-1 overflow-y-auto p-8 relative z-10">
          <div className="max-w-3xl mx-auto mt-6">
            
            {!generatedKey ? (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                {/* Header text */}
                <div>
                  <h2 className="text-2xl font-bold text-white mb-2">Select Duration</h2>
                  <p className="text-zinc-400 text-sm">Choose a standard preset or specify a custom duration for the new key.</p>
                </div>

                {/* Presets Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {PRESETS.map((preset) => {
                    const isSelected = selectedPreset === preset.id;
                    const Icon = preset.icon;
                    return (
                      <button
                        key={preset.id}
                        onClick={() => setSelectedPreset(preset.id)}
                        className={cn(
                          "relative text-left p-5 rounded-xl border transition-all duration-200 group flex flex-col items-start gap-4",
                          isSelected 
                            ? "bg-[#ff8c33]/10 border-[#ff8c33]/50 shadow-[0_0_20px_rgba(255,140,51,0.1)]" 
                            : "bg-zinc-900/50 border-zinc-800/80 hover:bg-zinc-800/50 hover:border-zinc-700"
                        )}
                      >
                        {preset.badge && (
                          <div className="absolute -top-2.5 right-3 px-2 py-0.5 bg-gradient-to-r from-[#ff8c33] to-[#e66a10] text-white text-[10px] font-bold tracking-wide uppercase rounded shadow-sm">
                            {preset.badge}
                          </div>
                        )}
                        
                        <div className={cn(
                          "p-2.5 rounded-lg border transition-colors",
                          isSelected ? "bg-[#ff8c33]/20 border-[#ff8c33]/30 text-[#ff8c33]" : "bg-zinc-800/50 border-zinc-700/50 text-zinc-400 group-hover:text-zinc-300"
                        )}>
                          <Icon className="w-5 h-5" />
                        </div>
                        
                        <div>
                          <div className={cn("font-semibold text-lg mb-0.5", isSelected ? "text-white" : "text-zinc-200")}>
                            {preset.label}
                          </div>
                          <div className={cn("text-xs", isSelected ? "text-[#ff8c33]/80" : "text-zinc-500")}>
                            {preset.desc}
                          </div>
                        </div>

                        {isSelected && (
                          <div className="absolute top-4 right-4">
                            <CheckCircle2 className="w-5 h-5 text-[#ff8c33]" />
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>

                {/* Custom Duration Fields (shown conditionally) */}
                {selectedPreset === "custom" && (
                  <div className="p-5 rounded-xl border border-zinc-800/80 bg-zinc-900/30 flex gap-4 animate-in fade-in slide-in-from-top-2">
                    <div className="flex-1 space-y-2">
                      <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Value</label>
                      <input 
                        type="number" 
                        defaultValue={14}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50"
                      />
                    </div>
                    <div className="flex-1 space-y-2">
                      <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Unit</label>
                      <select className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50 appearance-none">
                        <option>Days</option>
                        <option>Hours</option>
                        <option>Minutes</option>
                      </select>
                    </div>
                  </div>
                )}

                <div className="h-px bg-zinc-800/50 w-full" />

                {/* Note Field */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-zinc-300 flex items-center justify-between">
                    Internal Note
                    <span className="text-xs text-zinc-500 font-normal">Optional</span>
                  </label>
                  <input 
                    type="text" 
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="e.g. Customer discord tag, purpose, or reference..." 
                    className="w-full bg-zinc-900/50 border border-zinc-800 rounded-xl px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50 transition-all"
                  />
                </div>

                {/* Actions */}
                <div className="pt-4 flex items-center justify-end gap-4">
                  <button className="px-5 py-2.5 text-sm font-medium text-zinc-400 hover:text-white transition-colors">
                    Cancel
                  </button>
                  <button 
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="flex items-center gap-2 px-6 py-2.5 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-70 disabled:cursor-not-allowed group"
                  >
                    {isGenerating ? (
                      <>
                        <div className="w-4 h-4 border-2 border-orange-950/20 border-t-orange-950 rounded-full animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Generate Key
                        <ArrowRight className="w-4 h-4 opacity-70 group-hover:translate-x-0.5 transition-transform" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              /* Success State */
              <div className="max-w-2xl mx-auto mt-8 animate-in zoom-in-95 duration-400">
                <div className="bg-zinc-900/80 backdrop-blur-md border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl relative">
                  
                  {/* Success Banner */}
                  <div className="bg-emerald-500/10 border-b border-emerald-500/20 px-6 py-4 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <h3 className="text-emerald-400 font-medium">License Key Generated</h3>
                      <p className="text-emerald-500/70 text-xs mt-0.5">Ready to be sent to the customer</p>
                    </div>
                  </div>

                  {/* Key Display */}
                  <div className="p-8 flex flex-col items-center">
                    <div className="text-sm text-zinc-500 uppercase tracking-wider font-semibold mb-4">Your New Key</div>
                    
                    <div className="relative group w-full">
                      <div className="absolute inset-0 bg-gradient-to-r from-[#ff8c33]/20 via-[#ff8c33]/10 to-[#ff8c33]/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                      <div className="relative bg-[#0a0a0a] border border-zinc-800 rounded-xl p-6 flex flex-col items-center justify-center gap-4 group-hover:border-[#ff8c33]/30 transition-colors">
                        <code className="text-3xl sm:text-4xl font-mono font-bold text-white tracking-[0.1em] text-center break-all selection:bg-[#ff8c33]/30">
                          {generatedKey}
                        </code>
                        
                        <div className="flex items-center gap-3 mt-2">
                          <Badge variant="warning">{PRESETS.find(p => p.id === selectedPreset)?.label || "Custom Duration"}</Badge>
                          {note && <Badge variant="neutral" className="max-w-[200px] truncate">{note}</Badge>}
                        </div>
                      </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="flex flex-wrap items-center justify-center gap-3 mt-8 w-full">
                      <button 
                        onClick={handleCopy}
                        className={cn(
                          "flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-all border",
                          copied 
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                            : "bg-zinc-800 text-zinc-200 border-zinc-700 hover:bg-zinc-700 hover:text-white"
                        )}
                      >
                        {copied ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        {copied ? "Copied!" : "Copy Key"}
                      </button>
                      <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-zinc-800 text-zinc-200 border border-zinc-700 rounded-xl text-sm font-medium hover:bg-zinc-700 hover:text-white transition-all">
                        <Mail className="w-4 h-4 text-zinc-400" />
                        Email
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-zinc-800 text-zinc-200 border border-zinc-700 rounded-xl text-sm font-medium hover:bg-zinc-700 hover:text-white transition-all">
                        <QrCode className="w-4 h-4 text-zinc-400" />
                      </button>
                    </div>
                  </div>

                  <div className="bg-zinc-950/50 p-4 border-t border-zinc-800/80 flex justify-center">
                    <button 
                      onClick={handleReset}
                      className="text-sm font-medium text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Create another key
                    </button>
                  </div>

                </div>
              </div>
            )}

          </div>
        </div>
      </main>
    </div>
  );
}

// --- Subcomponents ---

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
