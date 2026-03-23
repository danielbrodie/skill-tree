"""Composite skill-tree header: image + type treatment."""

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Load base image
img = Image.open("header-v3.png").convert("RGBA")
w, h = img.size

# Create text overlay layer
overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

# Fonts — Exo 2 Black Italic (instanced at weight 900)
title_font = ImageFont.truetype("Exo2-BlackItalic.ttf", size=int(h * 0.16))
tagline_font = ImageFont.truetype("SpaceGrotesk-Variable.ttf", size=int(h * 0.045))

# Colors
title_color = (224, 247, 250, 245)  # light cyan, near-white
glow_color = (0, 188, 212, 80)      # cyan glow
tagline_color = (176, 190, 197, 200) # muted blue-grey

# Title: "skill-tree"
title_text = "skill-tree"
title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
title_w = title_bbox[2] - title_bbox[0]
title_h = title_bbox[3] - title_bbox[1]

# Position: lower-left with padding
pad_x = int(w * 0.06)
title_y = int(h * 0.58)

# Draw glow layer (blurred text behind)
glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_layer)
glow_draw.text((pad_x, title_y), title_text, font=title_font, fill=glow_color)
glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=12))

# Composite glow then sharp text
img = Image.alpha_composite(img, glow_layer)
overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)
draw.text((pad_x, title_y), title_text, font=title_font, fill=title_color)

# Tagline
tagline_text = "two-tier routing for agent skills at scale"
tagline_y = title_y + title_h + int(h * 0.03)
draw.text((pad_x + 4, tagline_y), tagline_text, font=tagline_font, fill=tagline_color)

# Final composite
result = Image.alpha_composite(img, overlay)
result = result.convert("RGB")
result.save("header-final.png", quality=95)
print(f"Saved header-final.png ({w}x{h})")
