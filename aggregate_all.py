import os
import json
import re

def aggregate_local_jsons():
    # Looks for any JSON files inside a 'raw_extractions' subfolder
    raw_dir = "./raw_extractions"
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir)
        print(f"Created '{raw_dir}' folder. Please place your raw chapter JSON extraction files there (e.g. ch001.json, ch002.json).")
        return {}

    results = {}
    
    # Process files
    for filename in os.listdir(raw_dir):
        if not filename.endswith(".json"):
            continue
            
        # Try to extract chapter number from filename
        match = re.search(r"ch(\d+)", filename, re.IGNORECASE)
        if not match:
            continue
            
        ch_num = int(match.group(1))
        ch_key = f"ch{ch_num:03d}"
        
        file_path = os.path.join(raw_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            results[ch_key] = {
                "folder": "local",
                "data": data,
                "error": None
            }
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            
    return results

if __name__ == "__main__":
    extracted = aggregate_local_jsons()
    print(f"Found {len(extracted)} aggregated chapters.")
    for ch, info in sorted(extracted.items()):
        items_count = len(info["data"]) if info["data"] else 0
        print(f"  {ch}: SUCCESS ({items_count} items)")
        
    # Write to status file
    with open("subagent_status.json", "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)
    print("Saved aggregation to 'subagent_status.json'")
