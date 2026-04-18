import React, { useState } from "react";
import {
  Search, ShieldAlert, Key, LayoutDashboard, History, Box, LogOut,
  Users, Server, Plus, UploadCloud, Play, Settings, FileCode2,
  ChevronDown, ChevronRight, MoreHorizontal, CheckCircle2,
  Activity, Download, RefreshCw, X, AlertCircle, Edit2, Trash2
} from "lucide-react";

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

const MOCK_CONFIGS = [
  { id: "cfg_1", name: "DenfiPortable", key: "DPRS-A1B2-C3D4", path: "C:\\Roblox\\Versions", hasIcon: true, url: "https://dprs.b-cdn.net", ota: "updated", version: "1.2.0", lastBuild: "2 hours ago" },
  { id: "cfg_2", name: "RobloxPro", key: "DPRS-X9Y8-Z7W6", path: "Not set", hasIcon: false, url: "https://api.roblox.pro", ota: "outdated", version: "1.1.8", lastBuild: "3 days ago" },
  { id: "cfg_3", name: "StudioClient", key: "DPRS-Q1W2-E3R4", path: "D:\\Games\\RBLX", hasIcon: true, url: "https://studio.api.net", ota: "downloading", version: "1.1.9", lastBuild: "1 day ago" },
  { id: "cfg_4", name: "LiteLauncher", key: "DPRS-M9N8-B7V6", path: "Not set", hasIcon: false, url: "https://dprs.b-cdn.net", ota: "updated", version: "1.2.0", lastBuild: "2 hours ago" },
  { id: "cfg_5", name: "BloxMod", key: "DPRS-P0O9-I8U7", path: "C:\\Program Files\\Blox", hasIcon: true, url: "https://mods.blox.net", ota: "failed", version: "1.1.5", lastBuild: "1 week ago" },
  { id: "cfg_6", name: "RblxOptimizer", key: "DPRS-L1K2-J3H4", path: "C:\\Optimizer", hasIcon: true, url: "https://dprs.b-cdn.net", ota: "updated", version: "1.2.0", lastBuild: "2 hours ago" },
  { id: "cfg_7", name: "VanillaPlus", key: "DPRS-Z9X8-C7V6", path: "Not set", hasIcon: false, url: "https://vanilla.plus.api", ota: "outdated", version: "1.1.0", lastBuild: "2 weeks ago" },
];

export function InventoryFirst() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expandedId, setExpandedId] = useState<string | null>("cfg_1");

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === MOCK_CONFIGS.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(MOCK_CONFIGS.map(c => c.id)));
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
            <NavItem icon={Key} label="Licenses" />
            <NavItem icon={Users} label="Customers" />
            <NavItem icon={Server} label="Infrastructure" />
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#0e0e11] relative">
        
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-zinc-800/50 bg-[#0e0e11] shrink-0">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-zinc-100">Build Configs</h1>
            <Badge variant="neutral">{MOCK_CONFIGS.length} Total</Badge>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input 
                type="text" 
                placeholder="Search configs..." 
                className="w-64 bg-zinc-900/50 border border-zinc-800 rounded-md py-1.5 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#ff8c33]/50 transition-all"
              />
            </div>
            <button className="flex items-center gap-2 px-3 py-1.5 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 rounded-md text-sm font-medium transition-colors">
              <Plus className="w-4 h-4" />
              New Config
            </button>
          </div>
        </header>

        {/* Layout split */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Inventory Grid (Left) */}
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="sticky top-0 bg-[#0e0e11] z-10 shadow-[0_1px_0_0_rgba(39,39,47,1)]">
                <tr className="text-zinc-500">
                  <th className="px-4 py-3 w-10">
                    <input 
                      type="checkbox" 
                      checked={selectedIds.size === MOCK_CONFIGS.length && MOCK_CONFIGS.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded border-zinc-700 bg-zinc-900 text-[#ff8c33] focus:ring-[#ff8c33]/50"
                    />
                  </th>
                  <th className="font-medium px-4 py-3">App Name</th>
                  <th className="font-medium px-4 py-3">License Key</th>
                  <th className="font-medium px-4 py-3">Server URL</th>
                  <th className="font-medium px-4 py-3">Path</th>
                  <th className="font-medium px-4 py-3 text-center">Icon</th>
                  <th className="font-medium px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/40 pb-20 block table-row-group">
                {MOCK_CONFIGS.map((cfg) => {
                  const isExpanded = expandedId === cfg.id;
                  const isSelected = selectedIds.has(cfg.id);
                  
                  return (
                    <React.Fragment key={cfg.id}>
                      <tr 
                        className={cn(
                          "transition-colors group",
                          isSelected ? "bg-[#ff8c33]/5" : "hover:bg-zinc-800/20"
                        )}
                      >
                        <td className="px-4 py-3">
                          <input 
                            type="checkbox" 
                            checked={isSelected}
                            onChange={() => toggleSelect(cfg.id)}
                            className="rounded border-zinc-700 bg-zinc-900 text-[#ff8c33] focus:ring-[#ff8c33]/50"
                          />
                        </td>
                        <td className="px-4 py-3 font-medium text-zinc-200">
                          <div className="flex items-center gap-2">
                            <button onClick={() => setExpandedId(isExpanded ? null : cfg.id)} className="text-zinc-500 hover:text-zinc-300">
                              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            </button>
                            {cfg.name}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <code className="font-mono text-xs text-zinc-400 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">
                            {cfg.key}
                          </code>
                        </td>
                        <td className="px-4 py-3 text-zinc-400 text-xs">{cfg.url}</td>
                        <td className="px-4 py-3 text-zinc-500 text-xs">{cfg.path}</td>
                        <td className="px-4 py-3 text-center">
                          {cfg.hasIcon ? <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" /> : <span className="text-zinc-600">-</span>}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button className="p-1.5 text-zinc-500 hover:text-zinc-300 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                            <MoreHorizontal className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                      
                      {/* Expanded Row */}
                      {isExpanded && (
                        <tr className="bg-zinc-900/30 border-b border-zinc-800/40">
                          <td></td>
                          <td colSpan={6} className="px-4 py-4">
                            <div className="flex items-center gap-8 pl-6">
                              <div className="flex flex-col gap-1">
                                <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">OTA Status</span>
                                <div className="flex items-center gap-1.5">
                                  {cfg.ota === 'updated' && <><div className="w-2 h-2 rounded-full bg-emerald-500"></div><span className="text-sm text-emerald-400">Up to date</span></>}
                                  {cfg.ota === 'outdated' && <><div className="w-2 h-2 rounded-full bg-amber-500"></div><span className="text-sm text-amber-400">Outdated</span></>}
                                  {cfg.ota === 'downloading' && <><Activity className="w-3 h-3 text-[#ff8c33] animate-pulse" /><span className="text-sm text-[#ff8c33]">Downloading</span></>}
                                  {cfg.ota === 'failed' && <><AlertCircle className="w-3 h-3 text-rose-500" /><span className="text-sm text-rose-400">Update Failed</span></>}
                                </div>
                              </div>
                              
                              <div className="w-px h-8 bg-zinc-800"></div>

                              <div className="flex flex-col gap-1">
                                <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Last Built</span>
                                <div className="flex items-center gap-2">
                                  <span className="text-sm text-zinc-300">v{cfg.version}</span>
                                  <span className="text-xs text-zinc-500">({cfg.lastBuild})</span>
                                </div>
                              </div>

                              <div className="w-px h-8 bg-zinc-800"></div>

                              <div className="flex items-center gap-2 ml-auto">
                                <button className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-md text-xs font-medium transition-colors">
                                  <Edit2 className="w-3.5 h-3.5" /> Edit
                                </button>
                                <button className="flex items-center gap-1.5 px-3 py-1.5 bg-[#ff8c33]/10 hover:bg-[#ff8c33]/20 text-[#ff8c33] rounded-md text-xs font-medium transition-colors">
                                  <Play className="w-3.5 h-3.5" /> Rebuild
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Sticky Rail (Right) */}
          <div className="w-[340px] border-l border-zinc-800/50 bg-[#0a0a0a] flex flex-col shrink-0 z-10 overflow-y-auto">
            
            {/* Launcher Source */}
            <div className="p-5 border-b border-zinc-800/50">
              <h3 className="text-sm font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                <FileCode2 className="w-4 h-4 text-zinc-500" />
                Launcher Source
              </h3>
              <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-lg p-3 mb-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-zinc-400">launcher.py</span>
                  <Badge variant="success">v1.2.0</Badge>
                </div>
                <div className="mt-2 text-[10px] text-zinc-500">Uploaded today at 09:41 AM</div>
              </div>
              <button className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-md text-xs font-medium border border-zinc-700/50 transition-colors">
                <UploadCloud className="w-4 h-4" />
                Upload New Version
              </button>
            </div>

            {/* Trigger Build */}
            <div className="p-5 border-b border-zinc-800/50">
              <h3 className="text-sm font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                <Play className="w-4 h-4 text-zinc-500" />
                Trigger Build
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-zinc-500 mb-1.5">Version Target</label>
                  <input type="text" defaultValue="1.2.1" className="w-full bg-zinc-900/50 border border-zinc-800 rounded-md py-1.5 px-3 text-sm text-zinc-100 focus:outline-none focus:border-[#ff8c33]/50 transition-all" />
                </div>
                <button className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 rounded-md text-sm font-bold shadow-sm transition-colors">
                  <RefreshCw className="w-4 h-4" />
                  Build All Configs
                </button>
              </div>
            </div>

            {/* Live Feed */}
            <div className="p-5 flex-1">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-500" />
                  Live Builds
                </h3>
                <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">v1.2.0</span>
              </div>

              <div className="space-y-3">
                <BuildProgressItem name="StudioClient" progress={100} status="completed" />
                <BuildProgressItem name="DenfiPortable" progress={100} status="completed" />
                <BuildProgressItem name="RobloxPro" progress={65} status="building" />
                <BuildProgressItem name="LiteLauncher" progress={0} status="pending" />
              </div>
            </div>

          </div>
        </div>

        {/* Sticky Bulk Action Bar */}
        {selectedIds.size > 0 && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-zinc-900 border border-zinc-700 shadow-xl rounded-lg px-4 py-3 flex items-center gap-4 animate-in slide-in-from-bottom-4 fade-in z-20">
            <div className="flex items-center gap-2 pr-4 border-r border-zinc-700">
              <div className="w-5 h-5 rounded-full bg-[#ff8c33]/20 flex items-center justify-center text-[#ff8c33] text-xs font-bold">
                {selectedIds.size}
              </div>
              <span className="text-sm font-medium text-zinc-200">Selected</span>
            </div>
            <button className="flex items-center gap-1.5 text-sm font-medium text-zinc-300 hover:text-zinc-100 transition-colors">
              <Settings className="w-4 h-4" /> Bulk Edit
            </button>
            <button className="flex items-center gap-1.5 text-sm font-medium text-zinc-300 hover:text-zinc-100 transition-colors">
              <Play className="w-4 h-4" /> Rebuild Selected
            </button>
            <button className="flex items-center gap-1.5 text-sm font-medium text-rose-400 hover:text-rose-300 transition-colors ml-2">
              <Trash2 className="w-4 h-4" /> Delete
            </button>
            <button 
              onClick={() => setSelectedIds(new Set())}
              className="ml-4 p-1 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded-md transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

      </main>
    </div>
  );
}

function NavItem({ icon: Icon, label, active }: { icon: any, label: string, active?: boolean }) {
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
    </button>
  );
}

function BuildProgressItem({ name, progress, status }: { name: string, progress: number, status: 'completed' | 'building' | 'pending' | 'failed' }) {
  return (
    <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-md p-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-medium text-zinc-300">{name}</span>
        <span className="text-[10px] text-zinc-500">
          {status === 'completed' && <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
          {status === 'building' && `${progress}%`}
          {status === 'pending' && 'Waiting'}
        </span>
      </div>
      <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
        <div 
          className={cn(
            "h-full rounded-full transition-all duration-500",
            status === 'completed' ? "bg-emerald-500" :
            status === 'building' ? "bg-[#ff8c33] animate-pulse" :
            "bg-zinc-700"
          )}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
