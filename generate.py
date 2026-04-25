import pandas as pd
import json
import os
import time
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='requests')

import requests
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env if it exists

from pypdf import PdfReader, PdfWriter
import io
from reportlab.pdfgen import canvas

key_index = 0

def call_llm(prompt: str, keys: list, retries_per_key: int = 5) -> str:
    global key_index
    url_template = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    
    last_exception = None
    max_global_retries = len(keys) * retries_per_key
    
    for attempt in range(max_global_retries):
        key = keys[key_index % len(keys)]
        if not key.strip():
            key_index = (key_index + 1) % len(keys)
            continue
            
        url = url_template.format(key.strip())
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                # Rotate to the next key to distribute load
                key_index = (key_index + 1) % len(keys)
                data = resp.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                return text
            elif resp.status_code in [429, 503]:
                print(f"    [!] API busy (Code {resp.status_code}) on key ...{key[-4:]}. Trying next key...")
                key_index = (key_index + 1) % len(keys)
                last_exception = Exception(f"HTTP {resp.status_code}: {resp.text}")
                
                # If we've completed a full cycle of all keys, apply exponential backoff
                if (attempt + 1) % max(len(keys), 1) == 0:
                    wait_time = (2 ** ((attempt + 1) // len(keys))) * 3
                    print(f"    [!] All keys busy. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                continue
            else:
                print(f"    [!] API Error {resp.status_code} on key ...{key[-4:]}. Switching key...")
                last_exception = Exception(f"API Error {resp.status_code}: {resp.text}")
                key_index = (key_index + 1) % len(keys)
                time.sleep(2)
                continue
        except Exception as e:
            last_exception = e
            print(f"    [!] Network error on key ...{key[-4:]}: {e}. Switching key...")
            key_index = (key_index + 1) % len(keys)
            time.sleep(2)
            
    raise Exception(f"All API keys and retries exhausted. Last error: {last_exception}")

def create_pdf(entries, output_filename="output.pdf"):
    coords_file = "overlay_coords.json"
    if not os.path.exists(coords_file):
        print(f"Error: {coords_file} not found. Please run 'python configure_coords.py' first!")
        return
        
    with open(coords_file, "r") as f:
        coords = json.load(f)
        
    template_path = "OJL_pdf.pdf"
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found.")
        return
        
    template_reader = PdfReader(template_path)
    writer = PdfWriter()
    
    def draw_wrapped_text(c, text, start_x, start_y, max_width=450):
        textobject = c.beginText()
        textobject.setTextOrigin(start_x, start_y)
        textobject.setFont("Helvetica", 11)
        textobject.setLeading(14)
        lines = []
        for raw_line in str(text).split('\\n'):
            words = raw_line.split()
            current_line = []
            for word in words:
                current_line.append(word)
                if c.stringWidth(' '.join(current_line), "Helvetica", 11) > max_width:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
        for L in lines:
            textobject.textLine(L)
        c.drawText(textobject)
        
    for i, entry in enumerate(entries):
        if i >= len(template_reader.pages):
            print(f"Warning: Only {len(template_reader.pages)} template pages available, but you have {len(entries)} entries. Extra entries will be skipped.")
            break
            
        page = template_reader.pages[i]
        
        # Create blank PDF canvas
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
        can.setFont("Helvetica", 11)
        
        def place_text(field_name, json_key=None, custom_val=None):
            if field_name not in coords: return
            
            # The config image was rendered at 150 DPI, but ReportLab works in 72 DPI.
            scale_factor = 72.0 / 150.0
            x = coords[field_name]['x'] * scale_factor
            y = (coords[field_name]['y'] * scale_factor) + 2 
            
            val = str(custom_val) if custom_val is not None else str(entry.get(json_key, ''))
            
            if field_name in ["my_space", "tasks_carried_out_today", "key_learnings_observations", "tools_technology_used", "special_achievements"]:
                is_half_column = field_name in ["tools_technology_used", "special_achievements"]
                page_width = float(page.mediabox.width)
                allowed_width = (page_width / 2.0) - 40 if is_half_column else page_width - x - 40
                
                draw_wrapped_text(can, val, x, y, max_width=allowed_width)
            else:
                can.drawString(x, y, val)
                
        place_text('date', 'date')
        timing = entry.get('oJT_timing', {})
        place_text('time_from', custom_val=timing.get('from', ''))
        place_text('time_to', custom_val=timing.get('to', ''))
        place_text('department', 'department')
        place_text('designation', 'designation')
        place_text('my_space', 'my_space')
        place_text('tasks_carried_out_today', 'tasks_carried_out_today')
        place_text('key_learnings_observations', 'key_learnings_observations')
        place_text('tools_technology_used', 'tools_technology_used')
        place_text('special_achievements', 'special_achievements')
        
        can.save()
        packet.seek(0)
        
        overlay_pdf = PdfReader(packet)
        overlay_page = overlay_pdf.pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    # Append any remaining blank template pages
    for i in range(len(entries), len(template_reader.pages)):
        writer.add_page(template_reader.pages[i])
        
    with open(output_filename, "wb") as output_stream:
        writer.write(output_stream)

def process_csv(csv_path, batch_size=5):
    df = pd.read_csv(csv_path)
    df = df.fillna("")
    records = df.to_dict(orient="records")
    
    all_entries = []
    keys_env = os.environ.get("GEMINI_API_KEYS", "")
    if not keys_env:
        keys = ["YOUR_PRIMARY_API_KEY", "YOUR_FALLBACK_API_KEY"]
    else:
        keys = [k.strip() for k in keys_env.split(",") if k.strip()]
    
    prompt_template = """
You are an expert content formatter. Convert the following daily internship logs into strict JSON.
Each log must be converted into a JSON object matching this EXACT schema:
{{
  "date": "string",
  "oJT_timing": {{
    "from": "string",
    "to": "string"
  }},
  "department": "string",
  "designation": "string",
  "my_space": "string",
  "tasks_carried_out_today": "string",
  "key_learnings_observations": "string",
  "tools_technology_used": "string",
  "special_achievements": "string"
}}

RULES:
- Return ONLY a JSON array of objects.
- Expand notes/bullet points into proper, professional sentences (2-5 sentences per field).
- Avoid repetition across days.
- Ensure the output strictly conforms to the schema.
- Do NOT wrap the JSON in markdown blocks like ```json.
- Output ONLY valid JSON format.

Here are the logs to process:
{logs}
"""
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        logs_str = json.dumps(batch, indent=2)
        prompt = prompt_template.format(logs=logs_str)
        
        try:
            result_text = call_llm(prompt, keys)
            
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            entries = json.loads(result_text)
            if isinstance(entries, list):
                all_entries.extend(entries)
            elif isinstance(entries, dict):
                for v in entries.values():
                    if isinstance(v, list):
                        all_entries.extend(v)
                        break
                else:
                    all_entries.append(entries)
            else:
                all_entries.append(entries)
                
        except Exception as e:
            print(f"Failed to process batch {i//batch_size + 1}: {e}")
            
    return all_entries

if __name__ == "__main__":
    csv_file = "input.csv"
    if os.path.exists(csv_file):
        print(f"Reading {csv_file}...")
        entries = process_csv(csv_file)
        if entries:
            create_pdf(entries, "output.pdf")
            print("Successfully saved output.pdf!")
        else:
            print("No valid entries were returned from the API.")
    else:
        print(f"Could not find {csv_file}")
