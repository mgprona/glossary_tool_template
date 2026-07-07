import os
import json
import re

# Paths
status_path = "subagent_status.json"
out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Manual entries (e.g., fallback data for chapters that failed or had errors)
# Example:
# manual_chapters = {
#     27: [ { "category": "Character", "korean_original": "...", "english_version": "...", ... } ]
# }
manual_chapters = {}

# Standard overrides for nomenclature to resolve translation inconsistencies
# Key: Korean Original -> values: Standard Thai/English translations to enforce
# Example:
# nomenclature_overrides = {
#     "화무기": {
#         "thai_version": "ฮวามูคี",
#         "english_version": "Hwa Mugi"
#     }
# }
nomenclature_overrides = {}

# Key canonicalization mapping (to merge name/title variants into a single entity)
# Key: Name variation -> Value: Canonical Korean name
# Example:
# canonical_keys = {
#     "이 공자": "검무극",
#     "이공자": "검무극"
# }
canonical_keys = {}

def load_all_chapters():
    if not os.path.exists(status_path):
        print(f"Error: {status_path} not found! Please run the aggregator script first.")
        return []
        
    with open(status_path, 'r', encoding='utf-8') as f:
        status_data = json.load(f)
        
    all_outputs = []
    
    # Process Chapters in order dynamically
    ch_keys = sorted([k for k in status_data.keys() if re.match(r"^ch\d+$", k)])
    
    for ch_key in ch_keys:
        ch_num = int(ch_key[2:])
        if ch_num in manual_chapters:
            all_outputs.append((ch_num, manual_chapters[ch_num]))
        else:
            ch_info = status_data[ch_key]
            if ch_info.get("data"):
                all_outputs.append((ch_num, ch_info["data"]))
    return all_outputs

def merge_glossary(outputs):
    merged = {}
    
    for ch_num, chapter in outputs:
        for entry in chapter:
            raw_key = entry["korean_original"].strip()
            match_key = re.sub(r'\s*\([^)]*\)', '', raw_key).strip()
            if not match_key:
                match_key = raw_key
                
            # Apply canonical key mapping
            canonical_key = canonical_keys.get(match_key, canonical_keys.get(raw_key, raw_key))
            raw_key = canonical_key
            match_key = re.sub(r'\s*\([^)]*\)', '', raw_key).strip()
            if not match_key:
                match_key = raw_key
                
            # Find if there is an existing entry
            found_key = None
            for k in merged.keys():
                k_clean = re.sub(r'\s*\([^)]*\)', '', k).strip()
                if k_clean == match_key or k == raw_key:
                    found_key = k
                    break
                    
            if not found_key:
                merged[raw_key] = {
                    "category": entry["category"].strip(),
                    "korean_original": raw_key,
                    "english_version": entry["english_version"].strip(),
                    "thai_version": entry["thai_version"].strip(),
                    "aliases": set(entry.get("aliases", [])),
                    "description": {
                        "en": entry["description"]["en"].strip(),
                        "th": entry["description"]["th"].strip()
                    },
                    "source_chapters": [ch_num]
                }
            else:
                existing = merged[found_key]
                existing["source_chapters"].append(ch_num)
                
                new_en = entry["english_version"].strip()
                if new_en != existing["english_version"]:
                    existing["aliases"].add(existing["english_version"])
                    if len(new_en) > len(existing["english_version"]):
                        existing["english_version"] = new_en
                    else:
                        existing["aliases"].add(new_en)
                        
                new_th = entry["thai_version"].strip()
                if new_th != existing["thai_version"]:
                    existing["aliases"].add(existing["thai_version"])
                    if len(new_th) > len(existing["thai_version"]):
                        existing["thai_version"] = new_th
                    else:
                        existing["aliases"].add(new_th)
                        
                if "aliases" in entry:
                    for alias in entry["aliases"]:
                        existing["aliases"].add(alias.strip())
                        
                if len(entry["description"]["en"]) > len(existing["description"]["en"]):
                    existing["description"]["en"] = entry["description"]["en"].strip()
                if len(entry["description"]["th"]) > len(existing["description"]["th"]):
                    existing["description"]["th"] = entry["description"]["th"].strip()

    # Apply standard overrides
    for k, v in list(merged.items()):
        # Find if raw_key or matched_key exists in overrides
        match_key = re.sub(r'\s*\([^)]*\)', '', k).strip()
        override_data = None
        for ok, ov in nomenclature_overrides.items():
            if ok == k or ok == match_key:
                override_data = ov
                break
                
        if override_data:
            # Store old values in aliases before overriding
            if v["thai_version"] != override_data["thai_version"]:
                v["aliases"].add(v["thai_version"])
            if v["english_version"] != override_data["english_version"]:
                v["aliases"].add(v["english_version"])
                
            # Perform override
            v["thai_version"] = override_data["thai_version"]
            v["english_version"] = override_data["english_version"]

    # Post-process: clean up aliases and convert sets to lists
    final_list = []
    for k, v in merged.items():
        clean_aliases = set()
        for alias in v["aliases"]:
            alias_clean = alias.strip()
            if (alias_clean and 
                alias_clean != v["english_version"] and 
                alias_clean != v["thai_version"] and 
                alias_clean != v["korean_original"]):
                clean_aliases.add(alias_clean)
        v["aliases"] = sorted(list(clean_aliases))
        v["source_chapters"] = sorted(list(set(v["source_chapters"])))
        final_list.append(v)
        
    return final_list

def generate_markdown(glossary_list, outputs):
    categories = {
        "Character": "👤 ตัวละคร (Characters)",
        "Location": "📍 สถานที่ (Locations)",
        "Organization": "⚔️ พรรค / นิกาย / ฝ่าย (Organizations & Sects)",
        "Item": "🔮 ไอเทม / สิ่งศักดิ์สิทธิ์ / อาวุธ (Items & Artifacts)",
        "Lore": "📜 ระบบพลัง / แนวคิดเฉพาะ (Lore & Concepts)"
    }
    
    max_ch = max([ch_num for ch_num, _ in outputs]) if outputs else 0
    
    md_content = "# คลังข้อมูลศัพท์นิยาย (Trilingual Glossary) - World Anvil Style\n\n"
    md_content += "> [!NOTE]\n"
    md_content += f"> คลังศัพท์นี้รวบรวมอย่างเป็นระบบผ่านระบบ Multi-agentic Pipeline จากบทที่ 1 ถึง {max_ch}\n"
    md_content += f"> จำนวนคำศัพท์ทั้งหมดในคลัง: {len(glossary_list)} รายการ\n\n"
    
    for cat_key, cat_title in categories.items():
        cat_entries = [e for e in glossary_list if e["category"] == cat_key]
        if not cat_entries:
            continue
            
        md_content += f"## {cat_title}\n\n"
        # Sort by Thai version
        for entry in sorted(cat_entries, key=lambda x: x["thai_version"]):
            aliases_str = f" (ชื่ออื่น: {', '.join(entry['aliases'])})" if entry["aliases"] else ""
            chapters_str = f" [ตอนที่ {', '.join(map(str, entry['source_chapters']))}]"
            md_content += f"*   **{entry['thai_version']}** | *{entry['english_version']}* ({entry['korean_original']}){aliases_str}{chapters_str}\n"
            md_content += f"    *   **รายละเอียด (TH):** {entry['description']['th']}\n"
            md_content += f"    *   **Description (EN):** {entry['description']['en']}\n"
        md_content += "\n"
        
    return md_content

if __name__ == "__main__":
    os.makedirs(out_dir, exist_ok=True)
    
    outputs = load_all_chapters()
    final_glossary = merge_glossary(outputs)
    
    # Write JSON
    json_out_path = os.path.join(out_dir, "glossary.json")
    with open(json_out_path, 'w', encoding='utf-8') as f:
        json.dump(final_glossary, f, ensure_ascii=False, indent=2)
        
    # Write Markdown
    md_out_path = os.path.join(out_dir, "glossary.md")
    md_text = generate_markdown(final_glossary, outputs)
    with open(md_out_path, 'w', encoding='utf-8') as f:
        f.write(md_text)
        
    print(f"SUCCESS: Generated glossary.json and glossary.md in {out_dir}")
    print(f"Total compiled unique items: {len(final_glossary)}")
