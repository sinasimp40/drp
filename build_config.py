import sys
import re
import os


def sanitize_exe_name(name):
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = sanitized.strip().strip('.')
    sanitized = sanitized.replace(' ', '')
    if not sanitized:
        sanitized = "RobloxLauncher"
    return sanitized


def encode_secret_xor(plaintext, xor_key=0x57):
    encoded = [ord(c) ^ xor_key for c in plaintext]
    hex_list = ','.join(f'0x{b:02x}' for b in encoded)
    return f"[{hex_list}]"


def main():
    if len(sys.argv) < 2:
        print("[ERROR] No path provided")
        sys.exit(1)

    roblox_path = sys.argv[1].strip().strip('"').strip("'")
    roblox_path = roblox_path.replace("\\", "/")

    app_name = ""
    if len(sys.argv) >= 3:
        app_name = sys.argv[2].strip().strip('"').strip("'")

    license_url = ""
    if len(sys.argv) >= 4:
        license_url = sys.argv[3].strip().strip('"').strip("'")

    license_secret = ""
    if len(sys.argv) >= 5:
        license_secret = sys.argv[4].strip().strip('"').strip("'")

    with open("launcher.py", "r", encoding="utf-8") as f:
        content = f.read()

    path_pattern = r'HARDCODED_PATH = ".*?"'
    path_replacement = f'HARDCODED_PATH = "{roblox_path}"'

    if re.search(path_pattern, content):
        content = re.sub(path_pattern, path_replacement, content)
    else:
        print("[ERROR] Could not find HARDCODED_PATH in launcher.py")
        sys.exit(1)

    if app_name:
        name_pattern = r'APP_NAME = ".*?"'
        name_replacement = f'APP_NAME = "{app_name}"'
        if re.search(name_pattern, content):
            content = re.sub(name_pattern, name_replacement, content)
        else:
            print("[ERROR] Could not find APP_NAME in launcher.py")
            sys.exit(1)

    if license_url:
        url_pattern = r'LICENSE_SERVER_URL = ".*?"'
        url_replacement = f'LICENSE_SERVER_URL = "{license_url}"'
        if re.search(url_pattern, content):
            content = re.sub(url_pattern, url_replacement, content)
        else:
            print("[ERROR] Could not find LICENSE_SERVER_URL in launcher.py")
            sys.exit(1)

    if license_secret:
        xor_encoded = encode_secret_xor(license_secret)
        xor_pattern = r'_LICENSE_SECRET_XOR = \[.*?\]'
        xor_replacement = f'_LICENSE_SECRET_XOR = {xor_encoded}'
        if re.search(xor_pattern, content):
            content = re.sub(xor_pattern, xor_replacement, content)
        else:
            print("[ERROR] Could not find _LICENSE_SECRET_XOR in launcher.py")
            sys.exit(1)

    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Path written: {roblox_path}")
    if app_name:
        exe_name = sanitize_exe_name(app_name)
        print(f"[OK] App name written: {app_name}")
        print(f"EXE_NAME={exe_name}")
    else:
        print(f"EXE_NAME=DenfiRoblox")
    if license_url:
        print(f"[OK] License server: {license_url}")
    if license_secret:
        print(f"[OK] License secret: (encoded and obfuscated)")


if __name__ == "__main__":
    main()
