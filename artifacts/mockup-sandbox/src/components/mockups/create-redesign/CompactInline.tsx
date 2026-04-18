import React, { useState, useEffect, useRef } from "react";
import { 
  ShieldAlert, LayoutDashboard, History, Box, Key, Users, Server, LogOut,
  Search, RotateCcw, ChevronRight, Plus, Copy, Check, Clock, CalendarDays,
  MoreVertical, RefreshCw, Zap
} from "lucide-react";

// --- Utility ---
function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

// --- Mock Data ---
const INITIAL_RECENT_KEYS = [
  { id: "1", key: "A1B2-C3D4-E5F6-G7H8", duration: "24", unit: "hours", note: "@shadow_dev test build", timestamp: "Just now" },
  { id: "2", key: "X9Y8-Z7W6-V5U4-T3S2", duration: "7", unit: "days", note: "client payload prep", timestamp: "2m ago" },
  { id: "3", key: "Q1W2-E3R4-T5Y6-U7I8", duration: "30", unit: "days", note: "@blox_master premium", timestamp: "15m ago" },
  { id: "4", key: "M9N8-B7V6-C5X4-Z3L2", duration: "12", unit: "hours", note: "temp session key", timestamp: "1h ago" },
  { id: "5", key: "P0O9-I8U7-Y6T5-R4E3", duration: "24", unit: "hours", note: "demo setup", timestamp: "3h ago" },
];

function generateMockKey() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let key = '';
  for (let i = 0; i < 16; i++) {
    if (i > 0 && i % 4 === 0) key += '-';
    key += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return key;
}

export function CompactInline() {
  const [duration, setDuration] = useState("24");
  const [unit, setUnit] = useState("hours");
  const [note, setNote] = useState("");
  const [recentKeys, setRecentKeys] = useState(INITIAL_RECENT_KEYS);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  
  const durationRef = useRef<HTMLInputElement>(null);

  const handleGenerate = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!duration || isGenerating) return;

    setIsGenerating(true);
    
    // Simulate network delay
    setTimeout(() => {
      const newKey = {
        id: Date.now().toString(),
        key: generateMockKey(),
        duration,
        unit,
        note: note || "No note provided",
        timestamp: "Just now"
      };
      
      setRecentKeys(prev => [newKey, ...prev].slice(0, 15));
      setNote("");
      setIsGenerating(false);
      
      // Auto-copy the new key
      handleCopy(newKey.key, newKey.id);
      
      // Focus back to duration
      durationRef.current?.focus();
    }, 400);
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // CMD+C or CTRL+C when not focused on an input could copy the latest key
      if ((e.metaKey || e.ctrlKey) && e.key === 'c') {
        const activeEl = document.activeElement;
        const isInput = activeEl?.tagName === 'INPUT' || activeEl?.tagName === 'TEXTAREA' || activeEl?.tagName === 'SELECT';
        
        if (!isInput && recentKeys.length > 0) {
          e.preventDefault();
          handleCopy(recentKeys[0].key, recentKeys[0].id);
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [recentKeys]);

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
              Workbench
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-xs font-mono text-zinc-500 flex items-center gap-2 mr-4 bg-zinc-900/50 px-3 py-1.5 rounded-md border border-zinc-800/50">
              <kbd className="font-sans px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">⌘</kbd>
              <kbd className="font-sans px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">C</kbd>
              <span>copies latest</span>
            </div>
            <div className="w-px h-5 bg-zinc-800 mx-1" />
            <button className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-300 hover:text-zinc-100 hover:bg-zinc-700 rounded-md text-sm font-medium border border-zinc-700/50 transition-colors">
              <RotateCcw className="w-4 h-4" />
              Recover Suspended
            </button>
          </div>
        </header>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-5xl mx-auto flex flex-col h-full">
            
            {/* Quick Create Bar */}
            <div className="bg-[#0a0a0a] border border-zinc-800 rounded-lg shadow-sm p-3 mb-6 relative overflow-hidden group">
              <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-[#ff8c33] to-[#e66a10]" />
              
              <form onSubmit={handleGenerate} className="flex items-center gap-3">
                <div className="flex items-center gap-2 pl-4 flex-shrink-0">
                  <Zap className="w-4 h-4 text-[#ff8c33]" />
                  <span className="text-sm font-medium text-zinc-300 mr-2">New Key</span>
                </div>
                
                <div className="flex items-center bg-zinc-900/80 border border-zinc-800 rounded-md overflow-hidden focus-within:ring-1 focus-within:ring-[#ff8c33]/50 focus-within:border-[#ff8c33]/50 transition-all flex-shrink-0">
                  <input 
                    ref={durationRef}
                    type="number" 
                    value={duration}
                    onChange={e => setDuration(e.target.value)}
                    className="w-16 bg-transparent py-2 pl-3 pr-1 text-sm text-zinc-100 focus:outline-none text-right font-mono"
                    min="1"
                    placeholder="24"
                    required
                  />
                  <select 
                    value={unit}
                    onChange={e => setUnit(e.target.value)}
                    className="bg-transparent py-2 pr-3 pl-1 text-sm text-zinc-400 focus:outline-none cursor-pointer hover:text-zinc-300"
                  >
                    <option value="minutes">mins</option>
                    <option value="hours">hours</option>
                    <option value="days">days</option>
                  </select>
                </div>
                
                <div className="flex-1 relative">
                  <input 
                    type="text" 
                    value={note}
                    onChange={e => setNote(e.target.value)}
                    placeholder="Note or reference (e.g. @user, payload type)..." 
                    className="w-full bg-zinc-900/80 border border-zinc-800 rounded-md py-2 px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50 transition-all"
                  />
                </div>
                
                <button 
                  type="submit" 
                  disabled={isGenerating}
                  className="flex items-center gap-2 px-6 py-2 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 disabled:opacity-50 disabled:cursor-not-allowed rounded-md text-sm font-medium shadow-sm transition-colors flex-shrink-0 min-w-[120px] justify-center"
                >
                  {isGenerating ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      Generate
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Session History List */}
            <div className="flex-1 bg-[#0a0a0a] border border-zinc-800/80 rounded-lg shadow-sm flex flex-col min-h-[400px]">
              <div className="px-5 py-4 border-b border-zinc-800/80 flex items-center justify-between bg-[#0e0e11]/50">
                <h2 className="text-sm font-medium text-zinc-100 flex items-center gap-2">
                  Session Activity
                  <span className="bg-zinc-800 text-zinc-400 text-xs px-2 py-0.5 rounded-full font-mono">
                    {recentKeys.length} keys
                  </span>
                </h2>
                <div className="text-xs text-zinc-500">
                  Resets on page reload
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto p-2">
                <div className="space-y-1">
                  {recentKeys.map((item, index) => (
                    <div 
                      key={item.id} 
                      className={cn(
                        "group flex items-center justify-between p-3 rounded-md transition-colors",
                        index === 0 
                          ? "bg-[#ff8c33]/5 border border-[#ff8c33]/20" 
                          : "hover:bg-zinc-800/30 border border-transparent"
                      )}
                    >
                      <div className="flex items-center gap-4 min-w-0">
                        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-zinc-900 border border-zinc-800/80 shrink-0">
                          <Key className={cn("w-3.5 h-3.5", index === 0 ? "text-[#ff8c33]" : "text-zinc-500")} />
                        </div>
                        
                        <div className="flex flex-col gap-1 min-w-0">
                          <div className="flex items-center gap-3">
                            <code className="font-mono text-sm font-medium text-zinc-200 tracking-wide">
                              {item.key}
                            </code>
                            <div className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-400 bg-zinc-900/80 px-2 py-0.5 rounded-sm border border-zinc-800/50">
                              {item.unit === "days" ? <CalendarDays className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                              {item.duration} {item.unit}
                            </div>
                            <span className="text-xs text-zinc-500 hidden sm:inline-block">
                              • {item.timestamp}
                            </span>
                          </div>
                          <div className="text-xs text-zinc-400 truncate max-w-md" title={item.note}>
                            {item.note}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 shrink-0">
                        <button 
                          onClick={() => handleCopy(item.key, item.id)}
                          className={cn(
                            "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                            copiedId === item.id 
                              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                              : "bg-zinc-900 text-zinc-400 border border-zinc-800 hover:text-zinc-200 hover:border-zinc-700 opacity-0 group-hover:opacity-100"
                          )}
                        >
                          {copiedId === item.id ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              Copy
                            </>
                          )}
                        </button>
                        <button className="p-1.5 text-zinc-500 hover:text-zinc-300 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                          <MoreVertical className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                  
                  {recentKeys.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-40 text-zinc-500">
                      <Key className="w-8 h-8 mb-3 opacity-20" />
                      <p className="text-sm">No keys generated this session.</p>
                      <p className="text-xs mt-1 opacity-60">Use the workbench above to create one.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

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
