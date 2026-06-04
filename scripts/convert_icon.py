import shutil
from PIL import Image

src = r"C:\Users\Zainy Zihar\.gemini\antigravity\brain\5327a8f6-3a67-440a-9c7e-62d3c57d9231\flowtrack_icon_1780610236627.png"
png_dest = r"e:\INDEX\PROGRAMMING NEW\Traffic flow Analysis GUI\traffic_analysis_gui\assets\icon.png"
ico_dest = r"e:\INDEX\PROGRAMMING NEW\Traffic flow Analysis GUI\traffic_analysis_gui\assets\icon.ico"

# Copy as PNG
shutil.copy2(src, png_dest)

# Convert to ICO
img = Image.open(src)
img.save(ico_dest, format="ICO", sizes=[(256, 256)])
print("Icon conversion successful!")
