import React, { useState, useEffect, useRef } from "react";
import { 
  Search, ShieldAlert, Key, LayoutDashboard, History, Box, LogOut, 
  Activity, Users, AlertTriangle, Clock, Server, Play, MoreHorizontal,
  Pause, Trash2, XCircle, CheckCircle2, ChevronRight, BarChart3, RotateCcw, Filter,
  UploadCloud, Terminal, Zap, FileCode2, HardDrive, Globe, RefreshCw, PenSquare, Eye
} from "lucide-react";

// --- UI Components Inline ---

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

const Badge = ({ children, variant = "default", className }: { children: React.ReactNode, variant?: "default" | "success" | "warning" | "danger" | "neutral" | "pending", className?: string }) => {
  const variants = {
    default: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    success: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    danger: "bg-rose-500/10 text-rose-500 border-rose-500/20",
    neutral: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    pending: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border uppercase tracking-wider", variants[variant], className)}>
      {children}
    </span>
  );
};

const MOCK_CONFIGS = [
  { id: "cfg_1", app_name: "DenfiPortable", license_key: "DPRS-A1B2-C3D4", path: "C:\\Program Files\\Roblox", has_icon: true, server_url: "https://api.dprs.net", status: "completed", progress: 100 },
  { id: "cfg_2", app_name: "RobloxPro", license_key: "DPRS-X9Y8-Z7W6", path: "C:\\Roblox", has_icon: true, server_url: "https://api.dprs.net", status: "completed", progress: 100 },
  { id: "cfg_3", app_name: "StudioClient", license_key: "DPRS-Q1W2-E3R4", path: "Not set", has_icon: false, server_url: "https://eu.dprs.net", status: "building", progress: 68 },
  { id: "cfg_4", app_name: "RBLX-Enterprise", license_key: "DPRS-M9N8-B7V6", path: "D:\\Games\\Roblox", has_icon: true, server_url: "https://api.dprs.net", status: "building", progress: 42 },
  { id: "cfg_5", app_name: "LiteLauncher", license_key: "DPRS-P0O9-I8U7", path: "Not set", has_icon: false, server_url: "https://us-east.dprs.net", status: "pending", progress: 0 },
  { id: "cfg_6", app_name: "DevTest_Env", license_key: "DPRS-L1K2-J3H4", path: "C:\\Dev\\Roblox", has_icon: true, server_url: "http://localhost:5000", status: "pending", progress: 0 },
  { id: "cfg_7", app_name: "SilentBoot", license_key: "DPRS-Z9X8-C7V6", path: "Not set", has_icon: true, server_url: "https://api.dprs.net", status: "pending", progress: 0 },
];

const MOCK_LOGS = [
  "[14:22:01] Starting global build process for v1.1.4",
  "[14:22:02] Loaded 7 build configurations",
  "[14:22:02] Verified launcher.py (checksum: 8f9a2b)",
  "[14:22:03] -> [DenfiPortable] Using cached icon resources",
  "[14:22:04] -> [DenfiPortable] Compiling executable...",
  "[14:22:09] -> [DenfiPortable] SUCCESS (4.2 MB)",
  "[14:22:10] -> [RobloxPro] Injecting license: DPRS-X9Y8-Z7W6",
  "[14:22:10] -> [RobloxPro] Compiling executable...",
  "[14:22:16] -> [RobloxPro] SUCCESS (4.3 MB)",
  "[14:22:17] -> [StudioClient] No icon found, using default fallback",
  "[14:22:17] -> [StudioClient] Compiling executable...",
  "[14:22:18] -> [RBLX-Enterprise] Injecting custom paths...",
  "[14:22:18] -> [RBLX-Enterprise] Compiling executable...",
];

export function CommandCockpit() {
  const [logs, setLogs] = useState(MOCK_LOGS);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

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
            <NavItem icon={Box} label="Builds" active />
          </div>

          <div className="space-y-1">
            <p className="px-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Management</p>
            <NavItem icon={Key} label="Create Key" actionIcon={ChevronRight} />
            <NavItem icon={Users} label="Customers" />
            <NavItem icon={Server} label="Infrastructure" />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#0e0e11]">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-zinc-800/50 bg-[#0e0e11] shrink-0 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-zinc-100 flex items-center gap-3">
              Build Management
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-300 hover:text-zinc-100 hover:bg-zinc-700 rounded-md text-sm font-medium border border-zinc-700/50 transition-colors">
              <Eye className="w-4 h-4" />
              Splash Preview
            </button>
            <button className="flex items-center gap-2 px-3 py-1.5 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 rounded-md text-sm font-medium shadow-sm transition-colors">
              <FileCode2 className="w-4 h-4" />
              New Config
            </button>
          </div>
        </header>

        {/* Split Screen Area */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Left 60%: Operator Controls */}
          <div className="w-[60%] border-r border-zinc-800/50 overflow-y-auto p-6 space-y-6">
            
            {/* Top Row: Source & Trigger */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-[#0a0a0a] border border-zinc-800/80 rounded-lg p-5 shadow-sm flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-medium text-zinc-100 flex items-center gap-2">
                    <FileCode2 className="w-4 h-4 text-zinc-500" />
                    Launcher Source
                  </h2>
                  <span className="text-xs text-zinc-500 font-mono">v1.1.4</span>
                </div>
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-md p-3 mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/10 rounded">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-zinc-300">launcher.py</p>
                      <p className="text-xs text-zinc-500">Last updated 2 days ago</p>
                    </div>
                  </div>
                </div>
                <button className="mt-auto w-full flex items-center justify-center gap-2 py-2 border border-zinc-700 border-dashed rounded-md text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-colors">
                  <UploadCloud className="w-4 h-4" />
                  Upload New Source
                </button>
              </div>

              <div className="bg-[#0a0a0a] border border-zinc-800/80 rounded-lg p-5 shadow-sm flex flex-col relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-[#ff8c33]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                <div className="flex items-center justify-between mb-4 relative z-10">
                  <h2 className="text-sm font-medium text-zinc-100 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-[#ff8c33]" />
                    Trigger Build
                  </h2>
                </div>
                <div className="space-y-4 relative z-10 flex-1 flex flex-col justify-between">
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 mb-1.5">Target Version</label>
                    <input 
                      type="text" 
                      defaultValue="1.1.5"
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-md py-2 px-3 text-sm text-zinc-100 font-mono focus:outline-none focus:border-[#ff8c33]/50 focus:ring-1 focus:ring-[#ff8c33]/50 transition-all"
                    />
                  </div>
                  <button className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 rounded-md text-sm font-bold shadow-[0_0_15px_rgba(255,140,51,0.2)] hover:shadow-[0_0_20px_rgba(255,140,51,0.4)] transition-all">
                    <Play className="w-4 h-4 fill-current" />
                    BUILD ALL CONFIGS
                  </button>
                </div>
              </div>
            </div>

            {/* Configs Table */}
            <div className="bg-[#0a0a0a] border border-zinc-800/80 rounded-lg shadow-sm overflow-hidden flex flex-col">
              <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/80">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-medium text-zinc-100">Build Configs</h2>
                  <span className="text-xs text-zinc-500 bg-zinc-900 px-2 py-0.5 rounded-full border border-zinc-800">7 total</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                    <input 
                      type="text" 
                      placeholder="Search configs..." 
                      className="w-48 bg-zinc-900 border border-zinc-800 rounded-md py-1 pl-8 pr-2 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                  <button className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded transition-colors" title="Bulk Edit">
                    <PenSquare className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead>
                    <tr className="border-b border-zinc-800/80 text-zinc-500 bg-[#0e0e11]/50">
                      <th className="w-8 px-4 py-2.5"><input type="checkbox" className="rounded bg-zinc-900 border-zinc-700" /></th>
                      <th className="font-medium px-4 py-2.5">App Name</th>
                      <th className="font-medium px-4 py-2.5">License</th>
                      <th className="font-medium px-4 py-2.5">Icon</th>
                      <th className="font-medium px-4 py-2.5">Server URL</th>
                      <th className="font-medium px-4 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/40">
                    {MOCK_CONFIGS.map((cfg) => (
                      <tr key={cfg.id} className="hover:bg-zinc-800/20 transition-colors group">
                        <td className="px-4 py-2.5"><input type="checkbox" className="rounded bg-zinc-900 border-zinc-700" /></td>
                        <td className="px-4 py-2.5 font-medium text-[#ff8c33]">{cfg.app_name}</td>
                        <td className="px-4 py-2.5">
                          <code className="font-mono text-[10px] text-zinc-400 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">
                            {cfg.license_key}
                          </code>
                        </td>
                        <td className="px-4 py-2.5">
                          {cfg.has_icon ? <span className="text-emerald-500">Yes</span> : <span className="text-zinc-600">No</span>}
                        </td>
                        <td className="px-4 py-2.5 text-zinc-500 truncate max-w-[120px]" title={cfg.server_url}>{cfg.server_url}</td>
                        <td className="px-4 py-2.5 text-right">
                          <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button className="p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors" title="Edit">
                              <PenSquare className="w-3.5 h-3.5" />
                            </button>
                            <button className="p-1 text-zinc-400 hover:text-blue-400 hover:bg-zinc-800 rounded transition-colors" title="Rebuild">
                              <RefreshCw className="w-3.5 h-3.5" />
                            </button>
                            <button className="p-1 text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 rounded transition-colors" title="Delete">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            
          </div>

          {/* Right 40%: Mission Control Telemetry */}
          <div className="w-[40%] bg-[#08080a] relative flex flex-col">
            {/* Subtle scanline overlay */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[linear-gradient(to_bottom,transparent_50%,#000_50%)] bg-[length:100%_4px] z-20" />
            
            <div className="p-4 border-b border-zinc-800/80 flex items-center justify-between bg-[#08080a] relative z-10">
              <div className="flex items-center gap-3">
                <div className="relative flex items-center justify-center w-2 h-2">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75 animate-ping"></span>
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                </div>
                <h2 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">Mission Control</h2>
              </div>
              <Badge variant="success">IN PROGRESS</Badge>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6 relative z-10">
              
              {/* In-Flight Build Progress */}
              <div>
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Global Build v1.1.5</h3>
                <div className="space-y-3">
                  {MOCK_CONFIGS.map((cfg) => (
                    <div key={cfg.id} className="bg-zinc-900/60 border border-zinc-800/80 rounded-md p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-zinc-300">{cfg.app_name}</span>
                        <span className={cn("text-[10px] font-mono", 
                          cfg.status === 'completed' ? "text-emerald-500" :
                          cfg.status === 'building' ? "text-[#ff8c33]" : "text-zinc-600"
                        )}>
                          {cfg.status === 'completed' ? 'DONE' : cfg.status === 'building' ? `${cfg.progress}%` : 'QUEUED'}
                        </span>
                      </div>
                      <div className="h-1.5 w-full bg-zinc-950 rounded-full overflow-hidden">
                        <div 
                          className={cn("h-full transition-all duration-500 ease-out rounded-full",
                            cfg.status === 'completed' ? "bg-emerald-500" :
                            cfg.status === 'building' ? "bg-gradient-to-r from-[#ff8c33] to-orange-400" : "bg-zinc-800"
                          )}
                          style={{ width: `${cfg.progress}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* OTA Heatmap */}
              <div>
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5" />
                  OTA Distribution
                </h3>
                <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-md p-4">
                  <div className="flex items-center justify-between text-[10px] text-zinc-500 mb-3">
                    <span>247 Total Licenses</span>
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded bg-emerald-500/80" /> v1.1.4</span>
                      <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded bg-amber-500/80" /> Updating</span>
                      <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded bg-zinc-700" /> Outdated</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-[repeat(auto-fill,minmax(12px,1fr))] gap-1">
                    {Array.from({ length: 120 }).map((_, i) => {
                      const rand = Math.random();
                      const status = rand > 0.8 ? 'updating' : rand > 0.15 ? 'updated' : 'outdated';
                      return (
                        <div 
                          key={i} 
                          className={cn("aspect-square rounded-sm opacity-80", 
                            status === 'updated' ? "bg-emerald-500" :
                            status === 'updating' ? "bg-amber-500 animate-pulse" : "bg-zinc-700"
                          )}
                          title={`License #${i} - ${status}`}
                        />
                      )
                    })}
                  </div>
                </div>
              </div>

            </div>

            {/* Terminal Log Tail */}
            <div className="h-48 border-t border-zinc-800/80 bg-black p-4 relative z-10 flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono text-zinc-600 uppercase">Compiler Output</span>
                <button className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors">Clear</button>
              </div>
              <div 
                ref={scrollRef}
                className="flex-1 overflow-y-auto font-mono text-[11px] leading-relaxed text-zinc-400 space-y-1"
              >
                {logs.map((log, i) => (
                  <div key={i} className={cn(
                    log.includes('SUCCESS') ? 'text-emerald-400/90' :
                    log.includes('->') ? 'text-zinc-300' : 'text-zinc-500'
                  )}>
                    {log}
                  </div>
                ))}
                <div className="text-[#ff8c33] animate-pulse">_</div>
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
