import React, { useState } from "react";
import { 
  Search, ShieldAlert, Key, LayoutDashboard, History, Box, LogOut, 
  Activity, Users, AlertTriangle, Clock, Server, Play, MoreHorizontal,
  Pause, Trash2, XCircle, CheckCircle2, ChevronRight, BarChart3, RotateCcw, Filter
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

// --- Mock Data ---

const MOCK_LICENSES = [
  { id: "lic_1", key: "DPRS-A1B2-C3D4-E5F6", status: "online", activated: "Apr 12, 2026 14:22", remaining: "29d 4h", timeStatus: "good", ip: "192.168.1.42", regIp: "192.168.1.42", lastSeen: "Just now", version: "1.0.1", note: "@bloxxer42 — premium tier" },
  { id: "lic_2", key: "DPRS-X9Y8-Z7W6-V5U4", status: "online", activated: "Apr 10, 2026 09:15", remaining: "27d 12h", timeStatus: "good", ip: "10.0.0.105", regIp: "10.0.0.105", lastSeen: "2 min ago", version: "1.0.1", note: "@nebula_dev — main project" },
  { id: "lic_3", key: "DPRS-Q1W2-E3R4-T5Y6", status: "offline", activated: "Mar 28, 2026 18:40", remaining: "15d 2h", timeStatus: "good", ip: "172.16.0.14", regIp: "172.16.0.14", lastSeen: "5 hrs ago", version: "1.0.0", note: "@ryan2009 — paid via PayPal" },
  { id: "lic_4", key: "DPRS-M9N8-B7V6-C5X4", status: "suspended", activated: "Apr 01, 2026 11:11", remaining: "18d 10h", timeStatus: "good", ip: "203.0.113.42", regIp: "198.51.100.12", lastSeen: "2 days ago", version: "1.0.1", note: "Suspicious IP jump detected" },
  { id: "lic_5", key: "DPRS-P0O9-I8U7-Y6T5", status: "online", activated: "Apr 15, 2026 08:00", remaining: "30d 0h", timeStatus: "good", ip: "8.8.8.8", regIp: "8.8.8.8", lastSeen: "Just now", version: "1.0.2-beta", note: "@admin_test — early access" },
  { id: "lic_6", key: "DPRS-L1K2-J3H4-G5F6", status: "online", activated: "Mar 15, 2026 14:20", remaining: "2d 5h", timeStatus: "warning", ip: "45.33.32.156", regIp: "45.33.32.156", lastSeen: "1 min ago", version: "1.0.1", note: "@devguy — renewing soon" },
  { id: "lic_7", key: "DPRS-Z9X8-C7V6-B5N4", status: "offline", activated: "Jan 12, 2026 10:00", remaining: "14h 22m", timeStatus: "danger", ip: "198.51.100.99", regIp: "198.51.100.99", lastSeen: "12 hrs ago", version: "0.9.8", note: "@olduser — remind to update" },
  { id: "lic_8", key: "DPRS-R4E3-W2Q1-A0S9", status: "pending", activated: "Not yet", remaining: "30d 0h", timeStatus: "neutral", ip: "N/A", regIp: "N/A", lastSeen: "Never", version: null, note: "Newly generated for @coolbuilder" },
  { id: "lic_9", key: "DPRS-U7Y6-T5R4-E3W2", status: "online", activated: "Apr 14, 2026 19:30", remaining: "29d 18h", timeStatus: "good", ip: "192.0.2.14", regIp: "192.0.2.14", lastSeen: "15 min ago", version: "1.0.1", note: "@studio_x — corporate license" },
  { id: "lic_10", key: "DPRS-I8O9-P0A1-S2D3", status: "suspended", activated: "Feb 20, 2026 16:45", remaining: "0d 0h", timeStatus: "danger", ip: "203.0.113.199", regIp: "198.51.100.5", lastSeen: "1 week ago", version: "1.0.0", note: "Chargeback received" },
];

export function SidebarSaas() {
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
            <NavItem icon={LayoutDashboard} label="Dashboard" active />
            <NavItem icon={History} label="History" />
            <NavItem icon={Box} label="Builds" />
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
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#0e0e11]">
        
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-zinc-800/50 bg-[#0e0e11] shrink-0 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-zinc-100 flex items-center gap-3">
              Licenses
              <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded-md border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live
              </span>
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative group">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2 group-focus-within:text-[#ff8c33] transition-colors" />
              <input 
                type="text" 
                placeholder="Search keys, IPs, or users..." 
                className="w-64 bg-zinc-900/50 border border-zinc-800 rounded-md py-1.5 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#ff8c33]/50 focus:border-[#ff8c33]/50 transition-all"
              />
            </div>
            <div className="w-px h-5 bg-zinc-800 mx-1" />
            <button className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-300 hover:text-zinc-100 hover:bg-zinc-700 rounded-md text-sm font-medium border border-zinc-700/50 transition-colors">
              <RotateCcw className="w-4 h-4" />
              Recover Suspended
            </button>
            <button className="flex items-center gap-2 px-3 py-1.5 bg-[#ff8c33] hover:bg-[#ff9d4d] text-orange-950 rounded-md text-sm font-medium shadow-sm transition-colors">
              <Key className="w-4 h-4" />
              Create Key
            </button>
          </div>
        </header>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-[1400px] mx-auto space-y-6">
            
            {/* KPI Strip */}
            <div className="grid grid-cols-4 gap-4">
              <KpiCard title="Total Licenses" value="247" trend="+12 this week" icon={Key} />
              <KpiCard 
                title="Online Now" 
                value="38" 
                trend="Peak: 45 today" 
                icon={Activity} 
                valueColor="text-emerald-400"
                sparkline
              />
              <KpiCard title="Suspended" value="6" trend="-2 from yesterday" icon={AlertTriangle} valueColor="text-amber-400" />
              <KpiCard title="Expiring < 24h" value="12" trend="Requires attention" icon={Clock} valueColor="text-rose-400" />
            </div>

            {/* Table Section */}
            <div className="bg-[#0a0a0a] border border-zinc-800/80 rounded-lg shadow-sm overflow-hidden flex flex-col">
              <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/80">
                <h2 className="text-sm font-medium text-zinc-100">All Licenses</h2>
                <div className="flex items-center gap-2">
                  <button className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded transition-colors">
                    <Filter className="w-4 h-4" />
                  </button>
                  <button className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded transition-colors">
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
                  <thead>
                    <tr className="border-b border-zinc-800/80 text-zinc-500 bg-[#0e0e11]/50">
                      <th className="font-medium px-5 py-3 w-[180px]">License Key</th>
                      <th className="font-medium px-5 py-3">Status</th>
                      <th className="font-medium px-5 py-3">Activated</th>
                      <th className="font-medium px-5 py-3">Time Remaining</th>
                      <th className="font-medium px-5 py-3">IP Address</th>
                      <th className="font-medium px-5 py-3">Last Seen</th>
                      <th className="font-medium px-5 py-3">Ver</th>
                      <th className="font-medium px-5 py-3 min-w-[200px]">Note</th>
                      <th className="font-medium px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/40">
                    {MOCK_LICENSES.map((lic) => (
                      <tr key={lic.id} className="hover:bg-zinc-800/20 transition-colors group">
                        <td className="px-5 py-3">
                          <code className="font-mono text-xs text-zinc-300 bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded cursor-copy hover:border-[#ff8c33]/50 hover:text-[#ff8c33] transition-colors">
                            {lic.key}
                          </code>
                        </td>
                        <td className="px-5 py-3">
                          {lic.status === "online" && <Badge variant="success" className="gap-1.5 pl-1.5"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>Online</Badge>}
                          {lic.status === "offline" && <Badge variant="neutral" className="gap-1.5 pl-1.5"><div className="w-1.5 h-1.5 rounded-full bg-zinc-500"></div>Offline</Badge>}
                          {lic.status === "suspended" && <Badge variant="warning" className="gap-1.5 pl-1.5"><div className="w-1.5 h-1.5 rounded-full bg-amber-500"></div>Suspended</Badge>}
                          {lic.status === "pending" && <Badge variant="default" className="gap-1.5 pl-1.5"><div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>Pending</Badge>}
                        </td>
                        <td className="px-5 py-3 text-zinc-400">
                          {lic.status === "pending" ? <span className="text-zinc-600 italic">Not yet</span> : lic.activated}
                        </td>
                        <td className="px-5 py-3">
                          <div className={cn(
                            "font-medium",
                            lic.status === "pending" ? "text-zinc-600" :
                            lic.timeStatus === "good" ? "text-zinc-300" :
                            lic.timeStatus === "warning" ? "text-amber-400" :
                            "text-rose-400"
                          )}>
                            {lic.remaining}
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex flex-col">
                            <span className={cn(lic.ip === "N/A" ? "text-zinc-600" : "text-zinc-300")}>{lic.ip}</span>
                            {lic.regIp !== "N/A" && lic.regIp !== lic.ip && (
                              <span className="text-[10px] text-zinc-500">Reg: {lic.regIp}</span>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3 text-zinc-400">{lic.lastSeen}</td>
                        <td className="px-5 py-3">
                          <span className={cn(lic.version ? "text-zinc-400" : "text-zinc-700")}>{lic.version || "-"}</span>
                        </td>
                        <td className="px-5 py-3 text-zinc-400 truncate max-w-[200px]" title={lic.note}>
                          {lic.note}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            {lic.status === "suspended" ? (
                              <button className="p-1.5 text-zinc-400 hover:text-emerald-400 hover:bg-zinc-800 rounded transition-colors" title="Unsuspend">
                                <Play className="w-4 h-4" />
                              </button>
                            ) : (
                              <button className="p-1.5 text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 rounded transition-colors" title="Suspend">
                                <Pause className="w-4 h-4" />
                              </button>
                            )}
                            <button className="p-1.5 text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 rounded transition-colors" title="Revoke">
                              <XCircle className="w-4 h-4" />
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

function KpiCard({ title, value, trend, icon: Icon, valueColor = "text-zinc-100", sparkline }: { title: string, value: string, trend: string, icon: any, valueColor?: string, sparkline?: boolean }) {
  return (
    <div className="bg-[#0a0a0a] border border-zinc-800/80 rounded-lg p-5 shadow-sm flex flex-col justify-between">
      <div className="flex items-start justify-between mb-4">
        <div className="p-2 bg-zinc-900 border border-zinc-800 rounded-md">
          <Icon className="w-4 h-4 text-zinc-400" />
        </div>
        {sparkline && (
          <div className="flex items-end gap-0.5 h-6 w-16 opacity-60">
            <div className="w-full bg-emerald-500/20 h-[30%] rounded-t-sm"></div>
            <div className="w-full bg-emerald-500/40 h-[50%] rounded-t-sm"></div>
            <div className="w-full bg-emerald-500/60 h-[40%] rounded-t-sm"></div>
            <div className="w-full bg-emerald-500/80 h-[80%] rounded-t-sm"></div>
            <div className="w-full bg-emerald-500 h-[100%] rounded-t-sm"></div>
          </div>
        )}
      </div>
      <div>
        <p className="text-sm font-medium text-zinc-500 mb-1">{title}</p>
        <div className="flex items-baseline gap-2">
          <h3 className={cn("text-2xl font-semibold tracking-tight", valueColor)}>{value}</h3>
          <span className="text-xs text-zinc-500">{trend}</span>
        </div>
      </div>
    </div>
  );
}
