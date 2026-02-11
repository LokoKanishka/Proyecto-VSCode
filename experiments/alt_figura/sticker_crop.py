from PIL import Image
import os

def sticker_crop_pro(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size
    pix = img.load()
    
    # Threshold to identify content vs background noise
    def is_noise(rgba):
        r, g, b, a = rgba
        # Dark pixels or low alpha considered noise - Increased AGGRESSION
        if a < 50: return True
        if r + g + b < 60: return True  # Strip very dark pixels
        return False

    # Force clear bottom 120px (the franja negra mentioned) - More aggressive
    for y in range(h - 120, h):
        for x in range(w):
            pix[x, y] = (0, 0, 0, 0)

    # Find tight BBox
    min_x, min_y = w, h
    max_x, max_y = 0, 0
    found = False

    for y in range(h):
        for x in range(w):
            if not is_noise(pix[x, y]):
                found = True
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y

    if not found:
        print("No content found!")
        return None

    # Apply 10px safety margin
    bbox = (max(0, min_x - 10), max(0, min_y - 10), min(w, max_x + 10), min(h, max_y + 10))
    cropped = img.crop(bbox)
    cropped.save(output_path, "PNG")
    print(f"Sticker Crop Size: {cropped.size}")
    return cropped.size

if __name__ == "__main__":
    project_dir = "/home/xdie/.gemini/antigravity/scratch/Proyecto-VSCode"
    source = os.path.join(project_dir, "alt_pure_transparent.png")
    # Using project_dir instead of project_root
    target = os.path.join(project_dir, "alt_figurita_base.png")
    sticker_crop_pro(source, target)
