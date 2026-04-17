import React, { useState } from "react";
import { 
  Activity, 
  Search, 
  RefreshCcw, 
  Plus, 
  LayoutDashboard, 
  History, 
  Box, 
  LogOut,
  Terminal,
  Server,
  AlertTriangle,
  Clock,
  Play,
  Pause,
  Trash2,
  MoreVertical,
  CheckCircle2,
  XCircle,
  Zap,
  Globe
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../ui/table";
import { Input } from "../../ui/input";
import { Button } from "../../ui/button";
import { Badge } from "../../ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../ui/dropdown-menu";
import { Progress } from "../../ui/progress";

const MOCK_LICENSES = [
  {
    id: "1",
    key: "DPRS-A1B2-C3D4-E5F6",
    status: "online",
    activated: "Apr 12, 2024 14:22",
    timeRemaining: "29d 4h",
    timeStatus: "good", // green
    lastIp: "192.168.1.45",
    registeredIp: "192.168.1.45",
    lastSeen: "Just now",
    version: "1.0.1",
    note: "@bloxxer42 — premium tier",
  },
  {
    id: "2",
    key: "DPRS-X9Y8-Z7W6-V5U4",
    status: "online",
    activated: "Jan 05, 2024 09:11",
    timeRemaining: "5d 12h",
    timeStatus: "warning", // amber
    lastIp: "203.0.113.8",
    registeredIp: "203.0.113.8",
    lastSeen: "2 min ago",
    version: "1.0.1",
    note: "@nebula_dev — renewed",
  },
  {
    id: "3",
    key: "DPRS-J5K6-L7M8-N9P0",
    status: "suspended",
    activated: "Mar 18, 2024 18:45",
    timeRemaining: "120d 0h",
    timeStatus: "good",
    lastIp: "198.51.100.22",
    registeredIp: "10.0.0.5",
    lastSeen: "4 hrs ago",
    version: "1.0.0",
    note: "@ryan2009 — IP mismatch detected",
  },
  {
    id: "4",
    key: "DPRS-Q1W2-E3R4-T5Y6",
    status: "offline",
    activated: "Feb 22, 2024 11:30",
    timeRemaining: "14h 30m",
    timeStatus: "danger", // red
    lastIp: "104.18.2.19",
    registeredIp: "104.18.2.19",
    lastSeen: "2 days ago",
    version: "1.0.1",
    note: "@builder_pro — trial ending",
  },
  {
    id: "5",
    key: "DPRS-M9N8-B7V6-C5X4",
    status: "pending",
    activated: "Not yet",
    timeRemaining: "30d 0h",
    timeStatus: "good",
    lastIp: "-",
    registeredIp: "-",
    lastSeen: "-",
    version: null,
    note: "@newuser99 — paid via PayPal",
  },
  {
    id: "6",
    key: "DPRS-F1G2-H3J4-K5L6",
    status: "online",
    activated: "Apr 01, 2024 08:00",
    timeRemaining: "20d 5h",
    timeStatus: "good",
    lastIp: "172.16.254.1",
    registeredIp: "172.16.254.1",
    lastSeen: "10 sec ago",
    version: "1.0.1",
    note: "@dev_king — trusted",
  },
  {
    id: "7",
    key: "DPRS-P0O9-I8U7-Y6T5",
    status: "online",
    activated: "Dec 15, 2023 16:20",
    timeRemaining: "2d 8h",
    timeStatus: "warning",
    lastIp: "192.0.2.146",
    registeredIp: "192.0.2.146",
    lastSeen: "1 min ago",
    version: "1.0.1",
    note: "@script_kiddie — check activity",
  },
  {
    id: "8",
    key: "DPRS-Z1X2-C3V4-B5N6",
    status: "suspended",
    activated: "Nov 10, 2023 10:10",
    timeRemaining: "45d 12h",
    timeStatus: "good",
    lastIp: "203.0.113.199",
    registeredIp: "198.51.100.50",
    lastSeen: "1 week ago",
    version: "0.9.8",
    note: "@hacker_man — chargeback",
  },
  {
    id: "9",
    key: "DPRS-L9K8-J7H6-G5F4",
    status: "offline",
    activated: "Oct 05, 2023 14:55",
    timeRemaining: "0d 2h",
    timeStatus: "danger",
    lastIp: "10.0.0.25",
    registeredIp: "10.0.0.25",
    lastSeen: "5 days ago",
    version: "1.0.0",
    note: "@robloxking — expiring soon",
  },
  {
    id: "10",
    key: "DPRS-R1E2-W3Q4-A5S6",
    status: "online",
    activated: "Apr 10, 2024 09:45",
    timeRemaining: "28d 14h",
    timeStatus: "good",
    lastIp: "172.16.0.5",
    registeredIp: "172.16.0.5",
    lastSeen: "Just now",
    version: "1.0.1",
    note: "@pro_creator",
  }
];

export function OperatorHud() {
  const [searchQuery, setSearchQuery] = useState("");

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "online":
        return <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 rounded-none font-mono uppercase text-[10px] tracking-wider px-2 py-0 h-5 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> ONL</Badge>;
      case "offline":
        return <Badge className="bg-slate-800 text-slate-400 border-slate-700 rounded-none font-mono uppercase text-[10px] tracking-wider px-2 py-0 h-5">OFF</Badge>;
      case "pending":
        return <Badge className="bg-blue-500/15 text-blue-400 border-blue-500/30 rounded-none font-mono uppercase text-[10px] tracking-wider px-2 py-0 h-5">PND</Badge>;
      case "suspended":
        return <Badge className="bg-red-500/15 text-red-400 border-red-500/30 rounded-none font-mono uppercase text-[10px] tracking-wider px-2 py-0 h-5 flex items-center gap-1"><XCircle className="w-3 h-3" /> SUS</Badge>;
      default:
        return <Badge variant="outline" className="rounded-none font-mono uppercase text-[10px]">{status}</Badge>;
    }
  };

  const getTimeColor = (status: string) => {
    switch (status) {
      case "good": return "text-emerald-400";
      case "warning": return "text-amber-400";
      case "danger": return "text-red-400";
      default: return "text-slate-300";
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-slate-300 font-sans selection:bg-[#ff8c33]/30 selection:text-white flex overflow-hidden">
      
      {/* SIDEBAR */}
      <aside className="w-60 border-r border-slate-800/60 bg-[#0d0d12] flex flex-col z-20 shrink-0">
        <div className="h-16 flex items-center px-4 border-b border-slate-800/60 shrink-0">
          <div className="flex items-center gap-2 text-[#ff8c33]">
            <Terminal className="w-5 h-5" />
            <span className="font-bold tracking-widest text-sm">DPRS_ADMIN</span>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-2 px-2">Core Systems</div>
          <button className="w-full flex items-center gap-3 px-2 py-2 rounded-sm bg-[#ff8c33]/10 text-[#ff8c33] text-sm font-medium transition-colors">
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </button>
          <button className="w-full flex items-center gap-3 px-2 py-2 rounded-sm text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 text-sm font-medium transition-colors">
            <History className="w-4 h-4" />
            History Log
          </button>
          <button className="w-full flex items-center gap-3 px-2 py-2 rounded-sm text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 text-sm font-medium transition-colors">
            <Box className="w-4 h-4" />
            Builds & Configs
          </button>

          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-2 px-2 mt-6">Actions</div>
          <button className="w-full flex items-center gap-3 px-2 py-2 rounded-sm text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 text-sm font-medium transition-colors">
            <Plus className="w-4 h-4" />
            Create Key
          </button>
        </nav>

        <div className="p-4 border-t border-slate-800/60 shrink-0">
          <button className="w-full flex items-center gap-3 px-2 py-2 rounded-sm text-slate-500 hover:text-slate-300 text-sm font-medium transition-colors">
            <LogOut className="w-4 h-4" />
            Operator Logout
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#0a0a0c]">
        
        {/* TOPBAR */}
        <header className="h-16 border-b border-slate-800/60 bg-[#0d0d12]/80 backdrop-blur flex items-center justify-between px-6 shrink-0 z-10 sticky top-0">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-slate-100 flex items-center gap-3">
              License Matrix
              <span className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-sm border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                System Live
              </span>
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input 
                type="text" 
                placeholder="Search keys, users, IPs..." 
                className="w-64 h-9 bg-[#121218] border border-slate-700/50 rounded-sm text-sm pl-9 pr-3 font-mono text-slate-300 focus:outline-none focus:border-[#ff8c33]/50 focus:ring-1 focus:ring-[#ff8c33]/20 transition-all placeholder:text-slate-600 placeholder:font-sans"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            <div className="h-5 w-px bg-slate-800 mx-1"></div>

            <Button variant="outline" className="h-9 rounded-sm border-amber-500/30 bg-amber-500/5 text-amber-400 hover:bg-amber-500/10 hover:text-amber-300 font-mono text-xs uppercase tracking-wide">
              <RefreshCcw className="w-3.5 h-3.5 mr-2" />
              Recover CDN (Fix)
            </Button>
            
            <Button className="h-9 rounded-sm bg-[#ff8c33] text-black hover:bg-[#ff9d4d] font-mono text-xs uppercase tracking-wide font-bold">
              <Plus className="w-3.5 h-3.5 mr-2" />
              Create Key
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-6 flex flex-col gap-6">
          
          {/* KPI STRIP */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 shrink-0">
            <Card className="bg-[#121218] border-slate-800/60 rounded-sm shadow-none">
              <CardContent className="p-4 flex flex-col justify-between h-full">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Total Licenses</span>
                  <Server className="w-4 h-4 text-slate-600" />
                </div>
                <div className="flex items-end gap-3">
                  <span className="text-3xl font-light text-slate-100 tracking-tight">247</span>
                  <span className="text-xs text-emerald-400 mb-1.5 font-mono">+12 today</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#121218] border-slate-800/60 rounded-sm shadow-none relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <CardContent className="p-4 flex flex-col justify-between h-full relative">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Online Now</span>
                  <Activity className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="flex items-end gap-3">
                  <span className="text-3xl font-light text-emerald-400 tracking-tight">38</span>
                  <div className="flex items-center gap-0.5 mb-2 h-4 w-16">
                    {[3, 7, 4, 8, 5, 9, 6, 10, 8, 12].map((h, i) => (
                      <div key={i} className="w-1 bg-emerald-500/40 rounded-t-sm" style={{ height: `${h * 10}%` }}></div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#121218] border-slate-800/60 rounded-sm shadow-none">
              <CardContent className="p-4 flex flex-col justify-between h-full">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Suspended</span>
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                </div>
                <div className="flex items-end gap-3">
                  <span className="text-3xl font-light text-red-400 tracking-tight">6</span>
                  <span className="text-xs text-slate-500 mb-1.5 font-mono">Requires action</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#121218] border-slate-800/60 rounded-sm shadow-none">
              <CardContent className="p-4 flex flex-col justify-between h-full">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Expiring &lt;24h</span>
                  <Clock className="w-4 h-4 text-amber-500" />
                </div>
                <div className="flex items-end gap-3">
                  <span className="text-3xl font-light text-amber-400 tracking-tight">12</span>
                  <span className="text-xs text-amber-500/70 mb-1.5 font-mono">-4% MoM</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* MAIN TABLE */}
          <Card className="bg-[#121218] border-slate-800/60 rounded-sm shadow-none flex-1 flex flex-col overflow-hidden min-h-[400px]">
            <div className="overflow-auto flex-1 custom-scrollbar">
              <Table className="relative w-full text-sm whitespace-nowrap">
                <TableHeader className="bg-[#0d0d12] sticky top-0 z-10 shadow-[0_1px_0_rgba(30,41,59,0.6)]">
                  <TableRow className="border-none hover:bg-transparent">
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">License Key</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">Status</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">Activated</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">Time Rem</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">IP Match</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">Last Seen</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">Ver</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4">Note / Customer</TableHead>
                    <TableHead className="font-mono text-[10px] uppercase tracking-widest text-slate-500 h-10 px-4 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {MOCK_LICENSES.map((lic) => (
                    <TableRow key={lic.id} className="border-slate-800/40 hover:bg-slate-800/20 group transition-colors">
                      <TableCell className="font-mono text-xs px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[#ff8c33]/90 select-all cursor-text">{lic.key}</span>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-2.5">{getStatusBadge(lic.status)}</TableCell>
                      <TableCell className="text-slate-400 text-xs px-4 py-2.5">{lic.activated}</TableCell>
                      <TableCell className={`font-mono text-xs px-4 py-2.5 ${getTimeColor(lic.timeStatus)}`}>
                        {lic.timeRemaining}
                      </TableCell>
                      <TableCell className="px-4 py-2.5">
                        <div className="flex flex-col gap-0.5">
                          <div className="flex items-center gap-1.5 font-mono text-xs text-slate-300">
                            {lic.lastIp !== lic.registeredIp && lic.lastIp !== "-" && <AlertTriangle className="w-3 h-3 text-red-400" />}
                            {lic.lastIp}
                          </div>
                          {lic.registeredIp !== "-" && (
                            <div className="font-mono text-[10px] text-slate-500 flex items-center gap-1">
                              <span className="w-1 h-1 border-l border-b border-slate-600 ml-1 mb-1"></span>
                              reg: {lic.registeredIp}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-400 text-xs px-4 py-2.5">{lic.lastSeen}</TableCell>
                      <TableCell className="px-4 py-2.5 text-xs">
                        {lic.version ? (
                          <span className="text-slate-300 font-mono">{lic.version}</span>
                        ) : (
                          <span className="text-slate-600">-</span>
                        )}
                      </TableCell>
                      <TableCell className="px-4 py-2.5 max-w-[200px] truncate text-slate-400 text-xs">
                        {lic.note}
                      </TableCell>
                      <TableCell className="px-4 py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {lic.status === 'suspended' && (
                            <Button variant="ghost" size="icon" className="h-7 w-7 rounded-sm hover:bg-emerald-500/10 hover:text-emerald-400 text-slate-400" title="Unsuspend">
                              <Play className="w-3.5 h-3.5" />
                            </Button>
                          )}
                          <Button variant="ghost" size="icon" className="h-7 w-7 rounded-sm hover:bg-amber-500/10 hover:text-amber-400 text-slate-400" title="Revoke">
                            <Pause className="w-3.5 h-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-7 w-7 rounded-sm hover:bg-red-500/10 hover:text-red-400 text-slate-400" title="Delete">
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-7 w-7 rounded-sm text-slate-400">
                                <MoreVertical className="w-3.5 h-3.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="bg-[#121218] border-slate-800 rounded-sm text-slate-300 min-w-[160px] font-mono text-xs">
                              <DropdownMenuLabel className="text-[10px] uppercase text-slate-500 tracking-widest">Key Actions</DropdownMenuLabel>
                              <DropdownMenuSeparator className="bg-slate-800" />
                              <DropdownMenuItem className="focus:bg-slate-800 focus:text-slate-200 cursor-pointer rounded-sm">Copy Key</DropdownMenuItem>
                              <DropdownMenuItem className="focus:bg-slate-800 focus:text-slate-200 cursor-pointer rounded-sm">View Logs</DropdownMenuItem>
                              <DropdownMenuItem className="focus:bg-slate-800 focus:text-slate-200 cursor-pointer rounded-sm">Reset IP Binding</DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            
            {/* TABLE FOOTER / STATUS STRIP */}
            <div className="h-8 border-t border-slate-800/60 bg-[#0d0d12] flex items-center justify-between px-4 shrink-0 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
              <div className="flex items-center gap-4">
                <span>Showing 10 of 247</span>
                <span className="flex items-center gap-1.5"><Globe className="w-3 h-3" /> CDN Status: Normal</span>
              </div>
              <div className="flex items-center gap-2">
                <span>Last Refreshed: {new Date().toLocaleTimeString()}</span>
              </div>
            </div>
          </Card>
        </div>
      </main>

      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #0a0a0c; 
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #1e1e28; 
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #2d2d3b; 
        }
      `}} />
    </div>
  );
}
