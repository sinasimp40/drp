import sys
import re

def main():
    if len(sys.argv) < 2:
        print("[ERROR] No path provided")
        sys.exit(1)

    roblox_path = sys.argv[1].strip().strip('"').strip("'")

    roblox_path = roblox_path.replace("\\", "/")

    with open("launcher.py", "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'HARDCODED_PATH = ".*?"'
    replacement = f'HARDCODED_PATH = "{roblox_path}"'

    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
    else:
        print("[ERROR] Could not find HARDCODED_PATH in launcher.py")
        sys.exit(1)

    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Path written: {roblox_path}")


if __name__ == "__main__":
    main()
