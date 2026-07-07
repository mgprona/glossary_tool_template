import os
import json
import re

# Paths
status_path = "subagent_status.json"
out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# UID category prefixes
CATEGORY_PREFIX = {
    "Character": "char",
    "Location": "loc",
    "Organization": "org",
    "Item": "item",
    "Lore": "lore"
}

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

# Entity relations for knowledge graph linking
# Key: Korean Original -> values: faction (Korean Original), entities (list of Korean Originals)
# These are resolved to UIDs during post-processing
# Example:
# entity_relations = {
#     "검무극": {
#         "faction": "화무결",
#         "associated_entities": ["검로아"]
#     }
# }
entity_relations = {
    # Example:
    # "검무극": {
    #     "faction": "화무결",
    #     "associated_entities": ["검로아", "천검"]
    # }
}

def generate_uid(category, english_version, counter):
    prefix = CATEGORY_PREFIX.get(category, "unk")
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', english_version.strip()).strip('_').lower()
    if not slug:
        slug = "unnamed"
    return f"{prefix}_{slug}_{counter:03d}"

def normalize_aliases(raw_aliases):
    if isinstance(raw_aliases, list):
        return {
            "titles": set(),
            "mis_translations": set(),
            "other_names": set(a.strip() for a in raw_aliases if a.strip())
        }
    if isinstance(raw_aliases, dict):
        return {
            "titles": set(raw_aliases.get("titles", [])),
            "mis_translations": set(raw_aliases.get("mis_translations", [])),
            "other_names": set(raw_aliases.get("other_names", []))
        }
    return {"titles": set(), "mis_translations": set(), "other_names": set()}

def empty_aliases():
    return {"titles": set(), "mis_translations": set(), "other_names": set()}

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
    uid_counters = {v: 0 for v in CATEGORY_PREFIX.values()}

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
                category = entry["category"].strip()
                en_version = entry["english_version"].strip()
                prefix = CATEGORY_PREFIX.get(category, "unk")
                uid_counters[prefix] += 1
                uid = generate_uid(category, en_version, uid_counters[prefix])

                merged[raw_key] = {
                    "uid": uid,
                    "category": category,
                    "korean_original": raw_key,
                    "english_version": en_version,
                    "thai_version": entry["thai_version"].strip(),
                    "aliases": normalize_aliases(entry.get("aliases", [])),
                    "description": {
                        "en": entry["description"]["en"].strip(),
                        "th": entry["description"]["th"].strip()
                    },
                    "source_chapters": [ch_num],
                    "faction_id": None,
                    "associated_entities": []
                }
            else:
                existing = merged[found_key]
                existing["source_chapters"].append(ch_num)

                new_en = entry["english_version"].strip()
                if new_en != existing["english_version"]:
                    existing["aliases"]["other_names"].add(existing["english_version"])
                    if len(new_en) > len(existing["english_version"]):
                        existing["english_version"] = new_en
                    else:
                        existing["aliases"]["other_names"].add(new_en)

                new_th = entry["thai_version"].strip()
                if new_th != existing["thai_version"]:
                    existing["aliases"]["other_names"].add(existing["thai_version"])
                    if len(new_th) > len(existing["thai_version"]):
                        existing["thai_version"] = new_th
                    else:
                        existing["aliases"]["other_names"].add(new_th)

                raw_aliases = entry.get("aliases", [])
                incoming = normalize_aliases(raw_aliases)
                for cat in ["titles", "mis_translations", "other_names"]:
                    existing["aliases"][cat].update(incoming[cat])

                if len(entry["description"]["en"]) > len(existing["description"]["en"]):
                    existing["description"]["en"] = entry["description"]["en"].strip()
                if len(entry["description"]["th"]) > len(existing["description"]["th"]):
                    existing["description"]["th"] = entry["description"]["th"].strip()

    # Apply standard overrides
    for k, v in list(merged.items()):
        match_key = re.sub(r'\s*\([^)]*\)', '', k).strip()
        override_data = None
        for ok, ov in nomenclature_overrides.items():
            if ok == k or ok == match_key:
                override_data = ov
                break

        if override_data:
            if v["thai_version"] != override_data["thai_version"]:
                v["aliases"]["other_names"].add(v["thai_version"])
            if v["english_version"] != override_data["english_version"]:
                v["aliases"]["other_names"].add(v["english_version"])

            v["thai_version"] = override_data["thai_version"]
            v["english_version"] = override_data["english_version"]

    # Build Korean-to-UID lookup
    ko_to_uid = {}
    for k, v in merged.items():
        match_key = re.sub(r'\s*\([^)]*\)', '', k).strip()
        ko_to_uid[k] = v["uid"]
        ko_to_uid[match_key] = v["uid"]

    # Apply entity relations
    for entity_ko, rel_data in entity_relations.items():
        match_ko = re.sub(r'\s*\([^)]*\)', '', entity_ko).strip()
        found_key = None
        for k in merged.keys():
            k_clean = re.sub(r'\s*\([^)]*\)', '', k).strip()
            if k_clean == match_ko or k == entity_ko:
                found_key = k
                break

        if found_key and found_key in merged:
            entry = merged[found_key]

            if "faction" in rel_data:
                faction_ko = rel_data["faction"]
                faction_uid = ko_to_uid.get(faction_ko,
                    ko_to_uid.get(re.sub(r'\s*\([^)]*\)', '', faction_ko).strip()))
                if faction_uid:
                    entry["faction_id"] = faction_uid

            if "associated_entities" in rel_data:
                for ae_ko in rel_data["associated_entities"]:
                    ae_uid = ko_to_uid.get(ae_ko,
                        ko_to_uid.get(re.sub(r'\s*\([^)]*\)', '', ae_ko).strip()))
                    if ae_uid and ae_uid != entry["uid"]:
                        entry["associated_entities"].append(ae_uid)

    # Post-process: clean up aliases and convert sets to lists
    final_list = []
    for k, v in merged.items():
        clean_aliases = {}
        all_used = {v["english_version"], v["thai_version"], v["korean_original"]}
        for cat in ["titles", "mis_translations", "other_names"]:
            cleaned = set()
            used_in_other_cats = set()
            for other_cat in ["titles", "mis_translations", "other_names"]:
                if other_cat != cat:
                    used_in_other_cats.update(
                        a.strip() for a in v["aliases"][other_cat]
                        if a.strip()
                    )
            for alias in v["aliases"][cat]:
                alias_clean = alias.strip()
                if (alias_clean and
                    alias_clean not in all_used and
                    alias_clean not in used_in_other_cats):
                    cleaned.add(alias_clean)
            clean_aliases[cat] = sorted(list(cleaned))

        v["aliases"] = clean_aliases
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
        for entry in sorted(cat_entries, key=lambda x: x["thai_version"]):
            alias_parts = []
            if entry["aliases"].get("titles"):
                alias_parts.append(f"ฉายา: {', '.join(entry['aliases']['titles'])}")
            if entry["aliases"].get("other_names"):
                alias_parts.append(f"ชื่ออื่น: {', '.join(entry['aliases']['other_names'])}")
            if entry["aliases"].get("mis_translations"):
                alias_parts.append(f"แปลผิด: {', '.join(entry['aliases']['mis_translations'])}")
            aliases_str = f" ({'; '.join(alias_parts)})" if alias_parts else ""

            chapters_str = f" [ตอนที่ {', '.join(map(str, entry['source_chapters']))}]"

            uid_str = f" `{entry['uid']}`"

            md_content += f"*   **{entry['thai_version']}** | *{entry['english_version']}* ({entry['korean_original']}){uid_str}{aliases_str}{chapters_str}\n"

            if entry.get("faction_id"):
                faction_name = next((e["thai_version"] for e in glossary_list if e["uid"] == entry["faction_id"]), entry["faction_id"])
                md_content += f"    *   **สังกัด:** {faction_name}\n"

            if entry.get("associated_entities"):
                entity_names = []
                for ae_uid in entry["associated_entities"]:
                    name = next((e["thai_version"] for e in glossary_list if e["uid"] == ae_uid), ae_uid)
                    entity_names.append(name)
                md_content += f"    *   **เกี่ยวข้องกับ:** {', '.join(entity_names)}\n"

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
