with open("extractframes.py", "r") as f:
    content = f.read()

# 1. Fix OpenCV QRCode detector crash
old_qr = """def extract_qr_text(rgb):
    detector = cv2.QRCodeDetector()

    data, points, _ = detector.detectAndDecode(rgb)"""

new_qr = """def extract_qr_text(rgb):
    detector = cv2.QRCodeDetector()

    try:
        data, points, _ = detector.detectAndDecode(rgb)
    except Exception as e:
        return None, None"""

content = content.replace(old_qr, new_qr)

# 2. Add try-except around demux loop and indent lines
lines = content.split('\n')
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "for packet in container.demux(stream):" in line:
        start_idx = i
    if start_idx != -1 and "frameIndex += 1" in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_lines = lines[:start_idx]
    new_lines.append("    try:")
    new_lines.append("        for packet in container.demux(stream):")
    new_lines.append("            for frame in packet.decode():")
    
    # indent inner block
    for i in range(start_idx + 2, end_idx + 1):
        if lines[i].strip():
            new_lines.append("    " + lines[i])
        else:
            new_lines.append(lines[i])
            
    new_lines.append("    except Exception as e:")
    new_lines.append('        logging.error(f"Video extraction aborted mid-way due to error: {e}. Saving partial results...")')
    
    new_lines.extend(lines[end_idx + 1:])
    
    with open("extractframes.py", "w") as f:
        f.write('\n'.join(new_lines))
    print("Fixed extractframes.py successfully")
else:
    print("Could not find block boundaries")
