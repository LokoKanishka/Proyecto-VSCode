from PIL import Image
import os

def precision_crop(input_path, output_path, alpha_threshold=20):
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    
    # Debug: Check corners
    pix = img.load()
    print(f"DEBUG: Corner pixels (0,0): {pix[0,0]}, (W-1, 0): {pix[width-1, 0]}, (0, H-1): {pix[0, height-1]}, (W-1, H-1): {pix[width-1, height-1]}")

    # Find the real content bounding box by scanning alpha
    min_x, min_y = width, height
    max_x, max_y = 0, 0
    
    found = False
    for y in range(height):
        for x in range(width):
            if pix[x, y][3] > alpha_threshold:
                found = True
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
                
    if not found:
        print("❌ CRITICAL: No content found with threshold!")
        return None

    # Apply small 5px padding
    bbox = (max(0, min_x - 5), max(0, min_y - 5), min(width, max_x + 5), min(height, max_y + 5))
    
    cropped = img.crop(bbox)
    cropped.save(output_path, "PNG")
    print(f"✅ Precision Crop Success!")
    print(f"BBox found: {bbox}")
    print(f"Old Size: {width}x{height} -> New Size: {cropped.size[0]}x{cropped.size[1]}")
    return bbox

if __name__ == "__main__":
    project_dir = "/home/xdie/.gemini/antigravity/scratch/Proyecto-VSCode"
    source = os.path.join(project_dir, "alt_pure_transparent.png")
    target = os.path.join(project_dir, "alt_figurita_base.png")
    precision_crop(source, target)
