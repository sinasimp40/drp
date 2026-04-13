====================================================
  ROBLOX PORTABLE LAUNCHER - README
====================================================

WHAT IS THIS?
--------------
This is a portable Roblox launcher. Instead of Roblox
being tied to one computer's installation, you put all
the Roblox files in a folder (like a USB drive), and
the launcher runs Roblox directly from that folder.

HOW TO SET UP:
--------------
1. Run "SetupPortableFolder.bat"
   - This creates the folder structure automatically

2. Copy your Roblox files into the "RobloxFiles" folder
   - Find your Roblox files at:
     %LOCALAPPDATA%\Roblox\Versions\[version-hash]\
   - Copy ALL files from that folder to RobloxFiles\

3. Run "Launch Roblox.bat" to start Roblox portably!

FOLDER STRUCTURE:
-----------------
RobloxPortable\
  ├── Launch Roblox.bat       <- Run this to launch!
  ├── RobloxFiles\            <- Put Roblox files here
  │   ├── RobloxPlayerBeta.exe
  │   ├── *.dll files
  │   └── (all other Roblox files)
  ├── Logs\                   <- Launch logs stored here
  └── Cache\                  <- Roblox data stored here
                                 (keeps it portable!)

NOTES:
------
- The launcher redirects Roblox's AppData to the Cache
  folder so your data stays with the portable folder.
- You can put the entire RobloxPortable folder on a USB
  drive and use it on any Windows computer.
- Logs are saved each time you launch so you can track
  any issues.

SUPPORT:
--------
Visit the launcher web page for more help and updates.

====================================================
