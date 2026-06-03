import re
import os

INPUT_FILE = r"static/index.html"
OUTPUT_FILE = INPUT_FILE

print(f"Loading {INPUT_FILE}...")
with open(INPUT_FILE, "r", encoding="utf-8") as fh:
    lines = fh.readlines()

total_lines = len(lines)
print(f"Loaded {total_lines} lines.")

# Helper to find first index matching a condition
def find_line(pattern, start_idx=0, end_idx=None):
    if end_idx is None:
        end_idx = len(lines)
    for idx in range(start_idx, end_idx):
        if pattern in lines[idx]:
            return idx
    return -1

# Locate all key markers dynamically
style_start = find_line("<style>")
ops_widget_comment = find_line("/* WIDGET PANEL DE CONTROL DE OPERARIOS */")
style_end = find_line("</style>", start_idx=style_start+1)
header_start = find_line("<header>")
nav_start = find_line("<nav>")
nav_end = find_line("</nav>", start_idx=nav_start+1)
main_start = find_line("<main>", start_idx=nav_end+1)
main_end = find_line("</main>", start_idx=main_start+1)
workspace_end = find_line("</div>", start_idx=main_end+1) # Should close .workspace right after </main>
body_end = find_line("</body>")

print(f"Detected markers:")
print(f" - style_start: {style_start} ({lines[style_start].strip() if style_start != -1 else 'NOT FOUND'})")
print(f" - ops_widget_comment: {ops_widget_comment} ({lines[ops_widget_comment].strip() if ops_widget_comment != -1 else 'NOT FOUND'})")
print(f" - style_end: {style_end} ({lines[style_end].strip() if style_end != -1 else 'NOT FOUND'})")
print(f" - header_start: {header_start} ({lines[header_start].strip() if header_start != -1 else 'NOT FOUND'})")
print(f" - nav_start: {nav_start} ({lines[nav_start].strip() if nav_start != -1 else 'NOT FOUND'})")
print(f" - nav_end: {nav_end} ({lines[nav_end].strip() if nav_end != -1 else 'NOT FOUND'})")
print(f" - main_start: {main_start} ({lines[main_start].strip() if main_start != -1 else 'NOT FOUND'})")
print(f" - main_end: {main_end} ({lines[main_end].strip() if main_end != -1 else 'NOT FOUND'})")
print(f" - workspace_end: {workspace_end} ({lines[workspace_end].strip() if workspace_end != -1 else 'NOT FOUND'})")
print(f" - body_end: {body_end} ({lines[body_end].strip() if body_end != -1 else 'NOT FOUND'})")

if -1 in [style_start, ops_widget_comment, style_end, header_start, nav_start, nav_end, main_start, main_end, workspace_end, body_end]:
    print("CRITICAL ERROR: One or more markers not found! Aborting.")
    exit(1)
