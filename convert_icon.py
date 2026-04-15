import sys
import os
from PIL import Image

def find_image():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)

    extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.tif', '.gif']

    icon_png = os.path.join(script_dir, "icon.png")
    if os.path.isfile(icon_png):
        return icon_png

    icon_images = []
    for f in os.listdir(script_dir):
        name, ext = os.path.splitext(f.lower())
        if name == "icon" and ext in extensions:
            icon_images.append(os.path.join(script_dir, f))

    if icon_images:
        return icon_images[0]

    candidates = []
    for f in os.listdir(script_dir):
        name, ext = os.path.splitext(f.lower())
        if ext in extensions and name != "icon":
            candidates.append(os.path.join(script_dir, f))

    if candidates:
        return candidates[0]
    return None


def convert_to_ico(image_path, output_path):
    img = Image.open(image_path)

    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

    icon_images = []
    for size in sizes:
        resized = img.copy()
        resized.thumbnail(size, Image.LANCZOS)
        canvas = Image.new('RGBA', size, (0, 0, 0, 0))
        offset = ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2)
        canvas.paste(resized, offset)
        icon_images.append(canvas)

    icon_images[0].save(
        output_path,
        format='ICO',
        sizes=[(s, s) for s, _ in sizes],
        append_images=icon_images[1:]
    )
    return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(script_dir, "icon.ico")

    image_path = find_image()
    if not image_path:
        if os.path.exists(ico_path):
            print(f"[OK] icon.ico already exists (no source image to reconvert)")
            return True
        print("[*] No image file found to convert")
        return False

    print(f"[*] Found image: {os.path.basename(image_path)}")
    print(f"[*] Converting to icon.ico...")

    try:
        convert_to_ico(image_path, ico_path)
        print(f"[OK] Created icon.ico from {os.path.basename(image_path)}")
        return True
    except Exception as e:
        print(f"[ERROR] Conversion failed: {e}")
        return False


if __name__ == "__main__":
    main()
