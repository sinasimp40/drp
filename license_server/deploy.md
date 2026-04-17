# Deployment Guide

This document covers extra setup steps for the license server, including how to make it faster for international customers.

---

## Speed Up the Server for International Customers (CTCP)

If your VPS is in one country (e.g. Russia) and your customers are in another country (e.g. Thailand, Philippines, Brazil), connections can be slow or unstable. Big downloads time out, updates fail, customers complain.

This is fixed by changing one setting in Windows called the **TCP Congestion Control algorithm**. We switch it from the slow default (**CUBIC**) to a faster one (**CTCP**) that is much better at handling long-distance internet links.

This change:

- Is **free**.
- Takes **2 minutes**.
- Requires **no changes** to your launcher .exe files.
- Works **immediately** — no reboot needed.
- Affects every new connection from this point on.

---

### What you need

- Your VPS running **Windows** (Windows Server 2016 or newer, or Windows 10/11).
- An RDP connection to the VPS as **Administrator**.

---

### Step 1 — Open PowerShell as Administrator

1. RDP into your VPS.
2. Click the Start menu, type **PowerShell**.
3. Right-click **Windows PowerShell** → choose **Run as Administrator**.
4. Click **Yes** if Windows asks for permission.

A blue PowerShell window opens. Use this for all the commands below.

---

### Step 2 — Check what you have right now

Paste this command and press Enter:

```powershell
Get-NetTCPSetting -SettingName Internet | Select SettingName, CongestionProvider, AutoTuningLevelLocal
```

You'll see something like this:

```
SettingName CongestionProvider AutoTuningLevelLocal
----------- ------------------ --------------------
Internet                 CUBIC               Normal
```

If it says **CUBIC**, you're on the slow default. Continue to Step 3.

If it already says **CTCP** or **BBR2**, you're already optimized — skip to Step 5.

---

### Step 3 — Change to CTCP (the main fix)

Paste this whole block at once and press Enter:

```powershell
Set-NetTCPSetting -SettingName Internet -CongestionProvider CTCP
Set-NetTCPSetting -SettingName InternetCustom -CongestionProvider CTCP
Set-NetTCPSetting -SettingName Internet -InitialCongestionWindow 10 -CongestionProvider CTCP
Set-NetTCPSetting -SettingName InternetCustom -InitialCongestionWindow 10

netsh int tcp set global autotuninglevel=normal
netsh int tcp set global rss=enabled
netsh int tcp set global ecncapability=enabled
netsh int tcp set global initialRto=2000
```

You should see a few `Ok.` lines. If you see warnings about `chimney` or `keepalivetime` being invalid — **ignore them**, those settings are deprecated on modern Windows.

---

### Step 4 — (Optional) Try BBR2 — even faster

BBR2 is newer and even better than CTCP, but only works on some Windows Server versions. Try it:

```powershell
Set-NetTCPSetting -SettingName Internet -CongestionProvider BBR2
```

- If no error appears → great, you got the best option.
- If you see "BBR2 is not a valid value" → no problem, stay on CTCP. CTCP is still a huge upgrade over CUBIC.

---

### Step 5 — Verify the change

Run the same check command from Step 2:

```powershell
Get-NetTCPSetting -SettingName Internet | Select SettingName, CongestionProvider, AutoTuningLevelLocal
```

You should now see:

```
SettingName CongestionProvider AutoTuningLevelLocal
----------- ------------------ --------------------
Internet                  CTCP               Normal
```

(Or `BBR2` if Step 4 worked.)

If the CongestionProvider column shows **CTCP** or **BBR2** — **you're done**. The change is already active for all new customer connections.

---

### Step 6 — Make sure the firewall allows your server port

Replace `3842` with whatever port your license server actually runs on:

```powershell
Remove-NetFirewallRule -DisplayName "License Server" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "License Server" -Direction Inbound -LocalPort 3842 -Protocol TCP -Action Allow
```

You should see output ending with `PrimaryStatus : OK`.

---

## What did this actually do?

Plain English: Windows was using a strategy called **CUBIC** to send data to your customers. CUBIC is fine for nearby connections, but on long international links it overreacts to small network hiccups — every time a single packet gets dropped, it slows way down, then takes a long time to speed back up. Result: slow, choppy downloads for far-away customers.

**CTCP** (Compound TCP) is a smarter strategy. It doesn't panic over occasional packet loss on long links, so it stays at higher speeds. Customers in Thailand, Philippines, or anywhere far from your VPS will get noticeably faster, more reliable connections — especially when downloading the .exe builds.

**Analogy:** CUBIC is a nervous driver who slams on the brakes every time the road gets bumpy, then slowly speeds back up. CTCP is an experienced driver who taps the brakes briefly and gets right back to highway speed. Same road — but the experienced driver gets there much faster.

---

## Troubleshooting

### "Set-NetTCPSetting is not recognized"

You opened a normal PowerShell window. Close it and re-open as **Administrator** (right-click → Run as Administrator).

### "Access denied"

Same as above — you must run PowerShell as Administrator.

### Customers still complain about slow downloads

The TCP tuning helps a lot but won't fix everything. If customers are very far from the VPS (like Russia → South America), you'll get the biggest speed boost from putting **Cloudflare** in front of your server. Cloudflare has data centers around the world, so a customer in Bangkok downloads from a Bangkok server instead of from Russia. See your hosting provider's documentation or ask for the Cloudflare setup guide.

### How do I undo it?

If for any reason you want to revert to the default:

```powershell
Set-NetTCPSetting -SettingName Internet -CongestionProvider CUBIC
Set-NetTCPSetting -SettingName InternetCustom -CongestionProvider CUBIC
```

---

## Quick reference card

| Action | Command |
|--------|---------|
| Check current setting | `Get-NetTCPSetting -SettingName Internet \| Select SettingName, CongestionProvider, AutoTuningLevelLocal` |
| Switch to CTCP | `Set-NetTCPSetting -SettingName Internet -CongestionProvider CTCP` |
| Switch to BBR2 (newer) | `Set-NetTCPSetting -SettingName Internet -CongestionProvider BBR2` |
| Revert to CUBIC | `Set-NetTCPSetting -SettingName Internet -CongestionProvider CUBIC` |
| Show all global TCP settings | `netsh int tcp show global` |
