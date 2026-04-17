import React, { useState } from "react";
import {
  Search,
  Activity,
  ShieldAlert,
  AlertTriangle,
  Clock,
  MoreVertical,
  Play,
  Trash2,
  Ban,
  LayoutDashboard,
  History,
  Box,
  Key,
  LogOut,
  ChevronDown,
  RefreshCw
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

// --- Mock Data ---
const KPIS = [
  { label: "Total Licenses", value: "247", icon: Key, color: "text-blue-400" },
  { label: "Online Now", value: "38", icon: Activity, color: "text-green-400", live: true },
  { label: "Suspended", value: "6", icon: ShieldAlert, color: "text-amber-400" },
  { label: "Expiring < 24h", value: "12", icon: Clock, color: "text-red-400" },
];

const LICENSES = [
  {
    id: "1",
    key: "DPRS-A1B2-C3D4-E5F6",
    status: "online",
    activated: "Apr 12, 2026 14:22",
    timeRemaining: "29d 4h",
    timeStatus: "good", // > 7d
    lastIp: "192.168.1.45",
    registeredIp: "192.168.1.45",
    lastSeen: "2 min ago",
    version: "1.0.1",
    note: "@bloxxer42 — premium tier",
  },
  {
    id: "2",
    key: "DPRS-X9Y8-Z7W6-V5U4",
    status: "online",
    activated: "Apr 10, 2026 09:15",
    timeRemaining: "5d 12h",
    timeStatus: "warning", // 1-7d
    lastIp: "10.0.0.23",
    registeredIp: "10.0.0.23",
    lastSeen: "15 min ago",
    version: "1.0.1",
    note: "@nebula_dev — monthly sub",
  },
  {
    id: "3",
    key: "DPRS-Q1W2-E3R4-T5Y6",
    status: "suspended",
    activated: "Mar 01, 2026 11:00",
    timeRemaining: "12d 6h",
    timeStatus: "good",
    lastIp: "172.16.0.5",
    registeredIp: "8.8.8.8", // Mismatch
    lastSeen: "1 day ago",
    version: "1.0.0",
    note: "@ryan2009 — possible leak",
  },
  {
    id: "4",
    key: "DPRS-M9N8-B7V6-C5X4",
    status: "offline",
    activated: "Apr 15, 2026 16:45",
    timeRemaining: "30d 0h",
    timeStatus: "good",
    lastIp: "192.168.0.100",
    registeredIp: "192.168.0.100",
    lastSeen: "4 hours ago",
    version: "1.0.1",
    note: "@ninja_pro — paid via PayPal",
  },
  {
    id: "5",
    key: "DPRS-L1K2-J3H4-G5F6",
    status: "pending",
    activated: "Not yet",
    timeRemaining: "30d 0h (waiting)",
    timeStatus: "neutral",
    lastIp: "-",
    registeredIp: "N/A",
    lastSeen: "-",
    version: "-",
    note: "@newuser99 — awaiting activation",
  },
  {
    id: "6",
    key: "DPRS-P9O8-I7U6-Y5T4",
    status: "online",
    activated: "Apr 05, 2026 08:30",
    timeRemaining: "18h 45m",
    timeStatus: "danger", // < 24h
    lastIp: "10.1.1.50",
    registeredIp: "10.1.1.50",
    lastSeen: "Just now",
    version: "1.0.1",
    note: "@builder_max — reminder sent",
  },
  {
    id: "7",
    key: "DPRS-Z1X2-C3V4-B5N6",
    status: "suspended",
    activated: "Feb 20, 2026 14:10",
    timeRemaining: "0d 0h",
    timeStatus: "danger",
    lastIp: "192.168.2.10",
    registeredIp: "192.168.1.10",
    lastSeen: "1 week ago",
    version: "0.9.8",
    note: "@hacker_kid — chargeback",
  },
  {
    id: "8",
    key: "DPRS-R9E8-W7Q6-A5S4",
    status: "online",
    activated: "Apr 14, 2026 22:00",
    timeRemaining: "28d 11h",
    timeStatus: "good",
    lastIp: "172.20.10.5",
    registeredIp: "172.20.10.5",
    lastSeen: "5 min ago",
    version: "1.0.1",
    note: "@robloxking — VIP member",
  },
  {
    id: "9",
    key: "DPRS-F1D2-S3A4-P5O6",
    status: "offline",
    activated: "Mar 15, 2026 13:20",
    timeRemaining: "2d 4h",
    timeStatus: "warning",
    lastIp: "10.5.0.2",
    registeredIp: "10.5.0.2",
    lastSeen: "2 days ago",
    version: "1.0.0",
    note: "@casual_gamer — rarely plays",
  },
  {
    id: "10",
    key: "DPRS-U9I8-O7P6-L5K4",
    status: "online",
    activated: "Apr 16, 2026 09:00",
    timeRemaining: "30d 0h",
    timeStatus: "good",
    lastIp: "192.168.100.25",
    registeredIp: "192.168.100.25",
    lastSeen: "1 min ago",
    version: "1.0.1",
    note: "@fresh_start — brand new",
  },
];

export function GlassyPremium() {
  return (
    <div className="min-h-screen bg-[#05050A] text-slate-200 font-sans selection:bg-[#ff8c33]/30 selection:text-[#ff8c33] overflow-hidden relative">
      {/* --- Ambient Background Effects --- */}
      {/* Deep radial gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-20%,_#1c103f_0%,_#05050A_60%)] pointer-events-none" />
      {/* Orange accent glow */}
      <div className="absolute top-[-20%] right-[-10%] w-[800px] h-[800px] bg-[#ff8c33]/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
      {/* Subtle noise texture */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none mix-blend-overlay" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' }} />

      <div className="relative z-10 flex h-screen">
        {/* --- Sidebar --- */}
        <aside className="w-64 flex flex-col border-r border-white/[0.05] bg-white/[0.01] backdrop-blur-xl">
          <div className="h-20 flex items-center px-6 border-b border-white/[0.05]">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#ff8c33] to-[#e65c00] flex items-center justify-center shadow-[0_0_15px_rgba(255,140,51,0.4)]">
                <ShieldAlert className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-sm tracking-wide text-white">DPRS ADMIN</h1>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest">License Manager</p>
              </div>
            </div>
          </div>

          <nav className="flex-1 px-3 py-6 space-y-1">
            <NavItem icon={LayoutDashboard} label="Dashboard" active />
            <NavItem icon={History} label="History" />
            <NavItem icon={Box} label="Builds" />
            <NavItem icon={Key} label="Create Key" />
          </nav>

          <div className="p-4 border-t border-white/[0.05]">
            <button className="flex items-center gap-3 px-3 py-2 w-full text-sm font-medium text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-white/[0.03]">
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </aside>

        {/* --- Main Content --- */}
        <main className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
          {/* Header */}
          <header className="h-20 flex items-center justify-between px-8 border-b border-white/[0.05] bg-white/[0.01] backdrop-blur-md">
            <div className="flex items-center gap-4">
              <h2 className="text-xl font-medium text-white tracking-tight flex items-center gap-3">
                Active Licenses
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span>
                </span>
              </h2>
            </div>

            <div className="flex items-center gap-4">
              <div className="relative group">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 transition-colors group-focus-within:text-[#ff8c33]" />
                <Input
                  placeholder="Search keys, users, IPs..."
                  className="w-64 bg-white/[0.03] border-white/[0.08] text-sm text-white placeholder:text-slate-500 pl-9 focus-visible:ring-1 focus-visible:ring-[#ff8c33]/50 focus-visible:border-[#ff8c33]/50 h-10 rounded-xl"
                />
              </div>
              <Button variant="outline" className="h-10 bg-white/[0.03] border-amber-500/30 text-amber-400 hover:bg-amber-500/10 hover:text-amber-300 rounded-xl">
                <RefreshCw className="w-4 h-4 mr-2" />
                Recover Suspended
              </Button>
              <Button className="h-10 bg-[#ff8c33] hover:bg-[#e65c00] text-white shadow-[0_0_20px_rgba(255,140,51,0.3)] rounded-xl font-medium">
                <Key className="w-4 h-4 mr-2" />
                Create Key
              </Button>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
            {/* KPI Strip */}
            <div className="grid grid-cols-4 gap-6 mb-8">
              {KPIS.map((kpi, i) => (
                <div key={i} className="relative group p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] backdrop-blur-xl overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <div className="flex justify-between items-start relative z-10">
                    <div>
                      <p className="text-sm font-medium text-slate-400 mb-1">{kpi.label}</p>
                      <h3 className="text-4xl font-light text-white tracking-tight flex items-baseline gap-2">
                        {kpi.value}
                        {kpi.live && (
                           <div className="flex items-end gap-0.5 h-4">
                             <div className="w-1 h-2 bg-green-500 rounded-full animate-[pulse_1s_ease-in-out_infinite]" />
                             <div className="w-1 h-3 bg-green-500 rounded-full animate-[pulse_1.2s_ease-in-out_infinite_0.2s]" />
                             <div className="w-1 h-4 bg-green-500 rounded-full animate-[pulse_0.9s_ease-in-out_infinite_0.4s]" />
                             <div className="w-1 h-2 bg-green-500 rounded-full animate-[pulse_1.1s_ease-in-out_infinite_0.1s]" />
                           </div>
                        )}
                      </h3>
                    </div>
                    <div className={`p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] ${kpi.color}`}>
                      <kpi.icon className="w-5 h-5" />
                    </div>
                  </div>
                  {/* Subtle inner glow matching the icon color */}
                  <div className={`absolute -bottom-8 -right-8 w-32 h-32 blur-[50px] opacity-20 pointer-events-none bg-current ${kpi.color}`} />
                </div>
              ))}
            </div>

            {/* Table Container */}
            <div className="rounded-2xl border border-white/[0.05] bg-white/[0.01] backdrop-blur-xl overflow-hidden shadow-2xl relative">
              {/* Subtle top edge highlight */}
              <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/[0.1] to-transparent" />
              
              <Table className="w-full">
                <TableHeader className="bg-white/[0.02] border-b border-white/[0.05]">
                  <TableRow className="hover:bg-transparent border-none">
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase pl-6">License Key</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase">Status</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase">Activated</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase">Remaining</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase">IP (Registered)</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase">Last Seen</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase">Version</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase">Note</TableHead>
                    <TableHead className="h-12 text-xs font-semibold text-slate-400 tracking-wider uppercase text-right pr-6">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {LICENSES.map((lic) => (
                    <TableRow key={lic.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors group">
                      <TableCell className="pl-6 py-4">
                        <code className="px-2 py-1 rounded-md bg-black/40 border border-white/[0.05] text-[#ff8c33] text-[13px] tracking-wider">
                          {lic.key}
                        </code>
                      </TableCell>
                      <TableCell className="py-4">
                        <StatusBadge status={lic.status} />
                      </TableCell>
                      <TableCell className="py-4 text-sm text-slate-300">
                        {lic.activated}
                      </TableCell>
                      <TableCell className="py-4">
                        <span className={`text-sm font-medium ${
                          lic.timeStatus === 'good' ? 'text-green-400' :
                          lic.timeStatus === 'warning' ? 'text-amber-400' :
                          lic.timeStatus === 'danger' ? 'text-red-400' : 'text-slate-400'
                        }`}>
                          {lic.timeRemaining}
                        </span>
                      </TableCell>
                      <TableCell className="py-4">
                        <div className="flex flex-col">
                          <span className="text-sm text-slate-200">{lic.lastIp}</span>
                          {lic.registeredIp !== 'N/A' && (
                            <span className={`text-[11px] ${lic.lastIp !== lic.registeredIp ? 'text-red-400 font-medium' : 'text-slate-500'}`}>
                              Reg: {lic.registeredIp}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="py-4 text-sm text-slate-300">
                        {lic.lastSeen}
                      </TableCell>
                      <TableCell className="py-4">
                        {lic.version !== '-' ? (
                          <Badge variant="outline" className="bg-[#ff8c33]/10 text-[#ff8c33] border-[#ff8c33]/20 text-[11px] font-mono">
                            v{lic.version}
                          </Badge>
                        ) : (
                          <span className="text-slate-600">-</span>
                        )}
                      </TableCell>
                      <TableCell className="py-4">
                        <span className="text-sm text-slate-400 truncate block max-w-[180px]" title={lic.note}>
                          {lic.note}
                        </span>
                      </TableCell>
                      <TableCell className="py-4 text-right pr-6">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-8 w-8 p-0 hover:bg-white/[0.05] text-slate-400 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity">
                              <span className="sr-only">Open menu</span>
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-40 bg-[#0f0f16] border-white/[0.08] text-slate-200 rounded-xl shadow-2xl backdrop-blur-xl">
                            {lic.status === 'suspended' && (
                              <>
                                <DropdownMenuItem className="text-green-400 focus:text-green-300 focus:bg-green-400/10 cursor-pointer">
                                  <Play className="mr-2 h-4 w-4" />
                                  <span>Unsuspend</span>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator className="bg-white/[0.05]" />
                              </>
                            )}
                            <DropdownMenuItem className="text-amber-400 focus:text-amber-300 focus:bg-amber-400/10 cursor-pointer">
                              <Ban className="mr-2 h-4 w-4" />
                              <span>Revoke</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-red-400 focus:text-red-300 focus:bg-red-400/10 cursor-pointer">
                              <Trash2 className="mr-2 h-4 w-4" />
                              <span>Delete</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </main>
      </div>

      {/* Global styles for custom scrollbar within this component scope */}
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}} />
    </div>
  );
}

// --- Helper Components ---

function NavItem({ icon: Icon, label, active }: { icon: React.ElementType, label: string, active?: boolean }) {
  return (
    <a
      href="#"
      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group relative overflow-hidden ${
        active 
          ? "text-white bg-white/[0.06] shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] border border-white/[0.05]" 
          : "text-slate-400 hover:text-white hover:bg-white/[0.03]"
      }`}
    >
      {active && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#ff8c33] rounded-r-full shadow-[0_0_10px_rgba(255,140,51,0.8)]" />
      )}
      <Icon className={`w-4 h-4 ${active ? "text-[#ff8c33]" : "text-slate-500 group-hover:text-slate-300"}`} />
      {label}
    </a>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'online':
      return (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-green-500/10 border border-green-500/20 text-green-400 text-[11px] font-medium uppercase tracking-wider">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_5px_rgba(74,222,128,0.5)] animate-pulse" />
          Online
        </div>
      );
    case 'offline':
      return (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-slate-400 text-[11px] font-medium uppercase tracking-wider">
          <div className="w-1.5 h-1.5 rounded-full bg-slate-500" />
          Offline
        </div>
      );
    case 'pending':
      return (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[11px] font-medium uppercase tracking-wider">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          Pending
        </div>
      );
    case 'suspended':
      return (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-medium uppercase tracking-wider">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_5px_rgba(251,191,36,0.5)]" />
          Suspended
        </div>
      );
    default:
      return null;
  }
}
