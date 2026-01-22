from PIL import Image
import os

def force_figurita_clean(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size
    pix = img.load()
    
    # Force clear a 20px border to kill corner noise
    border = 30
    for x in range(w):
        for y in range(border): pix[x, y] = (0,0,0,0) # Top
        for y in range(h-border, h): pix[x, y] = (0,0,0,0) # Bottom
    for y in range(h):
        for x in range(border): pix[x, y] = (0,0,0,0) # Left
        for x in range(w-border, w): pix[x, y] = (0,0,0,0) # Right
        
    # Re-calculate BBox
    min_x, min_y = w, h
    max_x, max_y = 0, 0
    found = False
    
    for y in range(h):
        for x in range(w):
            if pix[x, y][3] > 10: # Content threshold
                found = True
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
                
    if not found:
        print("❌ Still no content found after border clear.")
        return None
        
    bbox = (min_x, min_y, max_x + 1, max_y + 1)
    cropped = img.crop(bbox)
    cropped.save(output_path, "PNG")
    print(f"✅ FORCED FIGURITA CROP SUCCESS!")
    print(f"Old: {w}x{h} -> New: {cropped.size[0]}x{cropped.size[1]}")
    return cropped.size

if __name__ == "__main__":
    project_dir = "/home/xdie/.gemini/antigravity/scratch/Proyecto-VSCode"
    source = os.path.join(project_dir, "alt_pure_transparent.png")
    target = os.path.join(project_dir, "alt_figurita_base.png")
    force_figurita_clean(source, target)
