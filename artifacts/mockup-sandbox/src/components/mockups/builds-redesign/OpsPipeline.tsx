import React, { useState } from "react";
import { 
  Search, ShieldAlert, Key, LayoutDashboard, History, Box, LogOut, 
  Users, Server, Play, MoreHorizontal, FileCode, CheckCircle2, ChevronRight, 
  Filter, UploadCloud, Rocket, AlertTriangle, ArrowRight, Loader2, XCircle, 
  Trash2, Edit, Copy, Check
} from "lucide-react";

// --- UI Components Inline ---

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

const Badge = ({ children, variant = "default", className }: { children: React.ReactNode, variant?: "default" | "success" | "warning" | "danger" | "neutral", className?: string }) => {
  const variants = {
    default: "bg-[#ff8c33]/10 text-[#ff8c33] border-[#ff8c33]/20",
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

// --- Mock Data ---

const MOCK_CONFIGS = [
  { id: "cfg_1", appName: "DenfiPortable", license: "DPRS-A1B2-C3D4", path: "C:\\Roblox\\Versions", hasIcon: true, server: "https://dprs.b-cdn.net/", status: "active" },
  { id: "cfg_2", appName: "RobloxPro", license: "DPRS-X9Y8-Z7W6", path: "Auto-detect", hasIcon: true, server: "https://dprs.b-cdn.net/", status: "active" },
  { id: "cfg_3", appName: "BloxLauncher", license: "DPRS-Q1W2-E3R4", path: "C:\\Program Files\\Roblox", hasIcon: false, server: "https://alt.dprs.net/", status: "active" },
  { id: "cfg_4", appName: "StudioClient", license: "DPRS-M9N8-B7V6", path: "Auto-detect", hasIcon: true, server: "https://dprs.b-cdn.net/", status: "suspended" },
  { id: "cfg_5", appName: "RbxFast", license: "DPRS-P0O9-I8U7", path: "D:\\Games\\Roblox", hasIcon: true, server: "https://dprs.b-cdn.net/", status: "active" },
  { id: "cfg_6", appName: "DenfiLite", license: "DPRS-L1K2-J3H4", path: "Auto-detect", hasIcon: false, server: "https://dprs.b-cdn.net/", status: "active" },
];

const ACTIVE_BUILD_TASKS = [
  { id: 1, name: "DenfiPortable", status: "completed", progress: 100, size: "14.2 MB", error: null },
  { id: 2, name: "RobloxPro", status: "completed", progress: 100, size: "14.1 MB", error: null },
  { id: 3, name: "BloxLauncher", status: "building", progress: 68, size: null, error: null },
  { id: 4, name: "StudioClient", status: "building", progress: 32, size: null, error: null },
  { id: 5, name: "RbxFast", status: "failed", progress: 14, size: null, error: "Icon conversion failed (invalid format)" },
  { id: 6, name: "DenfiLite", status: "pending", progress: 0, size: null, error: null },
];

const OTA_STATUS = [
  { id: 1, appName: "DenfiPortable", license: "DPRS-A1B2-C3D4", currentVer: "1.0.1", latestVer: "1.0.2", state: "downloading", progress: 45 },
  { id: 2, appName: "RobloxPro", license: "DPRS-X9Y8-Z7W6", currentVer: "1.0.2", latestVer: "1.0.2", state: "updated", progress: 100 },
  { id: 3, appName: "BloxLauncher", license: "DPRS-Q1W2-E3R4", currentVer: "0.9.8", latestVer: "1.0.2", state: "outdated", progress: 0 },
];

export function OpsPipeline() {
  const [configs, setConfigs] = useState(MOCK_CONFIGS);
  const [selectedConfigs, setSelectedConfigs] = useState<string[]>([]);
  const [bulkEditOpen, setBulkEditOpen] = useState(false);

  const toggleSelectAll = () => {
    if (selectedConfigs.length === configs.length) {
      setSelectedConfigs([]);
    } else {
      setSelectedConfigs(configs.map(c => c.id));
    }
  };

  const toggleSelect = (id: string) => {
    if (selectedConfigs.includes(id)) {
      setSelectedConfigs(selectedConfigs.filter(i => i !== id));
    } else {
      setSelectedConfigs([...selectedConfigs, id]);
    }
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
            <NavItem icon={Box} label="Builds" active />
          </div>

          <div className="space-y-1">
            <p className="px-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Management</p>
            <NavItem icon={Key} label="Create Key" actionIcon={ChevronRight} />
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
        
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-zinc-800/50 bg-[#0e0e11] shrink-0 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-zinc-100 flex items-center gap-3">
              Ops Pipeline
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-300 hover:text-zinc-100 hover:bg-zinc-700 rounded-md text-sm font-medium border border-zinc-700/50 transition-colors">
              Splash Preview
            </button>
            <button className="flex items-center gap-2 px-3 py-1.5 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 rounded-md text-sm font-medium shadow-sm transition-colors">
              New Config
            </button>
          </div>
        </header>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-[1400px] mx-auto space-y-8">
            
            {/* Pipeline Metaphor Section */}
            <div className="flex items-stretch gap-4 w-full">
              {/* Stage 1 */}
              <div className="flex-1 bg-[#16161e] border border-zinc-800/80 rounded-xl p-5 flex flex-col relative group hover:border-zinc-700 transition-colors shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded bg-blue-500/10 flex items-center justify-center border border-blue-500/20 text-blue-400">
                    <FileCode className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-zinc-100 text-sm">1. Source</h3>
                </div>
                
                <div className="flex-1 flex flex-col justify-center space-y-4">
                  <div className="flex items-center justify-between bg-zinc-900/80 border border-zinc-800 rounded-lg p-3">
                    <div className="flex items-center gap-3">
                      <FileCode className="w-5 h-5 text-zinc-500" />
                      <div>
                        <div className="text-sm font-medium text-zinc-200">launcher.py</div>
                        <div className="text-xs text-zinc-500">v1.0.1 • Updated 2h ago</div>
                      </div>
                    </div>
                    <Badge variant="neutral">Active</Badge>
                  </div>
                  <button className="w-full flex items-center justify-center gap-2 py-2 border border-dashed border-zinc-700 text-sm font-medium text-zinc-400 rounded-lg hover:border-[#ff8c33]/50 hover:text-[#ff8c33] transition-colors bg-zinc-900/30 hover:bg-[#ff8c33]/5">
                    <UploadCloud className="w-4 h-4" />
                    Upload New Source
                  </button>
                </div>
                
                {/* Arrow */}
                <div className="absolute -right-4 top-1/2 -translate-y-1/2 w-4 flex items-center justify-center z-10 text-zinc-700 group-hover:text-zinc-500 transition-colors">
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>

              {/* Stage 2 */}
              <div className="flex-1 bg-[#16161e] border border-zinc-800/80 rounded-xl p-5 flex flex-col relative group hover:border-zinc-700 transition-colors shadow-sm ring-1 ring-[#ff8c33]/10">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded bg-[#ff8c33]/10 flex items-center justify-center border border-[#ff8c33]/20 text-[#ff8c33]">
                      <Rocket className="w-4 h-4" />
                    </div>
                    <h3 className="font-semibold text-zinc-100 text-sm">2. Trigger Build</h3>
                  </div>
                  <span className="flex items-center gap-1 text-[10px] uppercase font-bold tracking-wider text-[#ff8c33]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#ff8c33] animate-pulse"></span>
                    Ready
                  </span>
                </div>
                
                <div className="flex-1 flex flex-col justify-center space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-500">Target Version</label>
                    <input 
                      type="text" 
                      defaultValue="1.0.2" 
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-[#ff8c33] focus:ring-1 focus:ring-[#ff8c33]/50 transition-all font-mono"
                    />
                  </div>
                  <button className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 font-semibold rounded-lg shadow-sm transition-colors">
                    <Rocket className="w-4 h-4" />
                    Build All Configs (6)
                  </button>
                </div>
                
                {/* Arrow */}
                <div className="absolute -right-4 top-1/2 -translate-y-1/2 w-4 flex items-center justify-center z-10 text-zinc-700 group-hover:text-zinc-500 transition-colors">
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>

              {/* Stage 3 */}
              <div className="flex-1 bg-[#16161e] border border-zinc-800/80 rounded-xl p-5 flex flex-col group hover:border-zinc-700 transition-colors shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 text-emerald-400">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-zinc-100 text-sm">3. Distribution</h3>
                </div>
                
                <div className="flex-1 flex flex-col justify-center">
                  <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-4 flex flex-col items-center justify-center text-center space-y-2 h-full">
                    <div className="text-3xl font-bold tracking-tight text-zinc-100">
                      2<span className="text-zinc-500 text-xl font-medium">/6</span>
                    </div>
                    <div className="text-xs text-zinc-400 font-medium">Builds Completed</div>
                    
                    <div className="w-full h-1.5 bg-zinc-800 rounded-full mt-2 overflow-hidden flex">
                      <div className="h-full bg-emerald-500 w-[33%] rounded-l-full"></div>
                      <div className="h-full bg-[#ff8c33] w-[33%] animate-pulse"></div>
                      <div className="h-full bg-rose-500 w-[16%]"></div>
                    </div>
                    <div className="flex justify-between w-full text-[10px] text-zinc-500 mt-1 font-medium px-1">
                      <span>2 Success</span>
                      <span>2 Building</span>
                      <span>1 Failed</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Middle Section: Active Build & OTA */}
            <div className="grid grid-cols-3 gap-6">
              
              {/* Active Build Panel */}
              <div className="col-span-2 bg-[#0a0a0a] border border-zinc-800/80 rounded-xl shadow-sm overflow-hidden flex flex-col">
                <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/80 bg-[#16161e]">
                  <div className="flex items-center gap-3">
                    <h2 className="text-sm font-medium text-zinc-100">Active Build</h2>
                    <Badge variant="warning" className="gap-1.5"><Loader2 className="w-3 h-3 animate-spin" /> v1.0.2</Badge>
                  </div>
                  <div className="text-xs font-medium text-zinc-400">
                    Elapsed: 01:24
                  </div>
                </div>
                
                <div className="p-2 space-y-1 max-h-[300px] overflow-y-auto">
                  {ACTIVE_BUILD_TASKS.map((task) => (
                    <div key={task.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-zinc-800/30 transition-colors group">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium text-zinc-200 truncate">{task.name}</span>
                          <span className="text-xs text-zinc-500 font-mono">
                            {task.status === 'completed' && task.size ? task.size : `${task.progress}%`}
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                          <div 
                            className={cn(
                              "h-full rounded-full transition-all duration-500",
                              task.status === 'completed' ? "bg-emerald-500" :
                              task.status === 'failed' ? "bg-rose-500" :
                              "bg-gradient-to-r from-[#ff8c33] to-[#ff9d4d] animate-pulse"
                            )}
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                      </div>
                      <div className="w-24 shrink-0 flex items-center justify-end">
                        {task.status === 'completed' && <Badge variant="success" className="w-full justify-center">Done</Badge>}
                        {task.status === 'building' && <Badge variant="warning" className="w-full justify-center">Compiling</Badge>}
                        {task.status === 'pending' && <Badge variant="neutral" className="w-full justify-center">Pending</Badge>}
                        {task.status === 'failed' && <Badge variant="danger" className="w-full justify-center">Failed</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
                {/* Global Error if any */}
                <div className="px-5 py-3 border-t border-zinc-800/80 bg-rose-500/5 flex items-start gap-3">
                  <AlertTriangle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
                  <div className="text-sm text-rose-200">
                    <span className="font-medium">Error in RbxFast config:</span> Icon conversion failed (invalid format). Fix the icon in the config and click "Rebuild".
                  </div>
                </div>
              </div>

              {/* OTA Status */}
              <div className="col-span-1 bg-[#0a0a0a] border border-zinc-800/80 rounded-xl shadow-sm overflow-hidden flex flex-col">
                <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/80 bg-[#16161e]">
                  <h2 className="text-sm font-medium text-zinc-100 flex items-center gap-2">
                    OTA Live Status
                  </h2>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {OTA_STATUS.map(ota => (
                    <div key={ota.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-zinc-200">{ota.appName}</span>
                        <code className="text-[10px] text-zinc-500 px-1.5 py-0.5 bg-zinc-900 rounded border border-zinc-800">{ota.license.split('-')[0]}***</code>
                      </div>
                      
                      {ota.state === 'downloading' && (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-[#ff8c33] font-medium flex items-center gap-1">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Downloading v{ota.latestVer}
                            </span>
                            <span className="text-zinc-500">{ota.progress}%</span>
                          </div>
                          <div className="h-1 w-full bg-zinc-800 rounded-full overflow-hidden">
                            <div className="h-full bg-[#ff8c33]" style={{ width: `${ota.progress}%` }}></div>
                          </div>
                        </div>
                      )}
                      
                      {ota.state === 'updated' && (
                        <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium bg-emerald-500/10 px-2 py-1.5 rounded-md border border-emerald-500/20">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Up to date (v{ota.currentVer})
                        </div>
                      )}
                      
                      {ota.state === 'outdated' && (
                        <div className="flex items-center gap-2 text-xs text-rose-400 font-medium bg-rose-500/10 px-2 py-1.5 rounded-md border border-rose-500/20">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Outdated (v{ota.currentVer}) — Needs v{ota.latestVer}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Configs Inventory Table */}
            <div className="bg-[#0a0a0a] border border-zinc-800/80 rounded-xl shadow-sm overflow-hidden flex flex-col">
              <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/80 bg-[#16161e]">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-medium text-zinc-100">Build Configs</h2>
                  <Badge variant="neutral">{configs.length}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  {selectedConfigs.length > 0 && (
                    <>
                      <button className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 text-zinc-300 hover:text-zinc-100 hover:bg-zinc-700 rounded-md text-xs font-medium border border-zinc-700/50 transition-colors">
                        Rebuild Selected ({selectedConfigs.length})
                      </button>
                      <button 
                        onClick={() => setBulkEditOpen(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/10 text-blue-500 hover:bg-blue-600/20 hover:text-blue-400 rounded-md text-xs font-medium border border-blue-500/20 transition-colors"
                      >
                        Bulk Edit ({selectedConfigs.length})
                      </button>
                      <div className="w-px h-4 bg-zinc-800 mx-1" />
                    </>
                  )}
                  <div className="relative group">
                    <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2 group-focus-within:text-[#ff8c33] transition-colors" />
                    <input 
                      type="text" 
                      placeholder="Search configs..." 
                      className="w-48 bg-zinc-900 border border-zinc-800 rounded-md py-1.5 pl-8 pr-3 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50 transition-all"
                    />
                  </div>
                </div>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead>
                    <tr className="border-b border-zinc-800/80 text-zinc-500 bg-zinc-900/30">
                      <th className="px-5 py-3 w-10">
                        <input 
                          type="checkbox" 
                          className="rounded bg-zinc-900 border-zinc-700 text-[#ff8c33] focus:ring-[#ff8c33]/50 focus:ring-offset-0"
                          checked={selectedConfigs.length === configs.length && configs.length > 0}
                          onChange={toggleSelectAll}
                        />
                      </th>
                      <th className="font-medium px-5 py-3">App Name</th>
                      <th className="font-medium px-5 py-3">License Key</th>
                      <th className="font-medium px-5 py-3">Hardcoded Path</th>
                      <th className="font-medium px-5 py-3">Icon</th>
                      <th className="font-medium px-5 py-3">Server URL</th>
                      <th className="font-medium px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/40">
                    {configs.map((c) => (
                      <tr key={c.id} className={cn("hover:bg-zinc-800/20 transition-colors group", selectedConfigs.includes(c.id) && "bg-blue-500/5 hover:bg-blue-500/10")}>
                        <td className="px-5 py-3">
                          <input 
                            type="checkbox" 
                            className="rounded bg-zinc-900 border-zinc-700 text-[#ff8c33] focus:ring-[#ff8c33]/50 focus:ring-offset-0"
                            checked={selectedConfigs.includes(c.id)}
                            onChange={() => toggleSelect(c.id)}
                          />
                        </td>
                        <td className="px-5 py-3 font-semibold text-zinc-200">{c.appName}</td>
                        <td className="px-5 py-3">
                          <code className="font-mono text-[11px] text-zinc-300 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded cursor-copy hover:border-[#ff8c33]/50 hover:text-[#ff8c33] transition-colors">
                            {c.license}
                          </code>
                        </td>
                        <td className="px-5 py-3 text-xs text-zinc-400 truncate max-w-[200px]" title={c.path}>{c.path}</td>
                        <td className="px-5 py-3">
                          {c.hasIcon 
                            ? <span className="text-emerald-500 font-medium text-xs bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Yes</span>
                            : <span className="text-zinc-500 text-xs">No</span>
                          }
                        </td>
                        <td className="px-5 py-3 text-xs text-zinc-400">{c.server}</td>
                        <td className="px-5 py-3 text-right">
                          <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button className="p-1.5 text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 rounded transition-colors" title="Edit">
                              <Edit className="w-4 h-4" />
                            </button>
                            <button className="p-1.5 text-zinc-400 hover:text-[#ff8c33] hover:bg-zinc-800 rounded transition-colors" title="Rebuild">
                              <Rocket className="w-4 h-4" />
                            </button>
                            <button className="p-1.5 text-zinc-400 hover:text-rose-500 hover:bg-zinc-800 rounded transition-colors" title="Delete">
                              <Trash2 className="w-4 h-4" />
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
        </div>

        {/* Bulk Edit Modal */}
        {bulkEditOpen && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-[#16161e] border border-zinc-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
              <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center">
                <h3 className="text-lg font-semibold text-zinc-100">Bulk Edit Configs</h3>
                <button onClick={() => setBulkEditOpen(false)} className="text-zinc-500 hover:text-zinc-300">
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 space-y-5">
                <p className="text-sm text-zinc-400">
                  Updating <strong className="text-zinc-200">{selectedConfigs.length}</strong> selected config(s). Tick a box to apply that field.
                </p>
                
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-zinc-300 cursor-pointer">
                      <input type="checkbox" className="rounded bg-zinc-900 border-zinc-700 text-[#ff8c33] focus:ring-[#ff8c33]/50 focus:ring-offset-0" />
                      Update Server URL
                    </label>
                    <input type="text" placeholder="https://dprs.b-cdn.net/" className="w-full bg-zinc-900/50 border border-zinc-800 rounded-md py-2 px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50" />
                  </div>

                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-zinc-300 cursor-pointer">
                      <input type="checkbox" className="rounded bg-zinc-900 border-zinc-700 text-[#ff8c33] focus:ring-[#ff8c33]/50 focus:ring-offset-0" />
                      Update Shared Secret
                    </label>
                    <input type="password" placeholder="••••••••••••••••" className="w-full bg-zinc-900/50 border border-zinc-800 rounded-md py-2 px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50" />
                  </div>
                </div>

                <div className="pt-2 border-t border-zinc-800/80">
                  <label className="flex items-start gap-2 text-sm text-zinc-300 cursor-pointer">
                    <input type="checkbox" className="rounded bg-zinc-900 border-zinc-700 text-[#ff8c33] focus:ring-[#ff8c33]/50 focus:ring-offset-0 mt-0.5" defaultChecked />
                    <div>
                      <span className="font-medium text-zinc-200">Rebuild selected configs after applying</span>
                      <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                        Rebuilds use the version from launcher.py (currently <strong className="text-zinc-400">v1.0.1</strong>).
                      </p>
                    </div>
                  </label>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-zinc-800 bg-[#0a0a0a] flex justify-end gap-3">
                <button onClick={() => setBulkEditOpen(false)} className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-zinc-100 transition-colors">
                  Cancel
                </button>
                <button onClick={() => setBulkEditOpen(false)} className="px-4 py-2 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 font-semibold rounded-md shadow-sm transition-colors flex items-center gap-2">
                  <Check className="w-4 h-4" />
                  Apply Changes
                </button>
              </div>
            </div>
          </div>
        )}

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
