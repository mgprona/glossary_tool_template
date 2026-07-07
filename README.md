# 🛠️ คู่มือใช้งานเทมเพลตระบบสกัดคำศัพท์นิยาย (Generic Trilingual Glossary Template)

โฟลเดอร์นี้คือ **เวอร์ชันเปล่า (Template)** สำหรับเริ่มต้นโครงการสกัดคำศัพท์นิยาย 3 ภาษา (เกาหลีต้นฉบับ / อังกฤษแปล / ไทยแปล) เพื่อสร้างคลังศัพท์ (Glossary) ตามมาตรฐาน World Anvil เพื่อนำไปใช้งานกับ AI สำหรับงานแปลต่อ เพื่อป้องกันไม่ให้ AI เกิดการหลอน (Hallucination) หรือใช้สรรพนามและคำศัพท์ที่ไม่สอดคล้องกัน

---

## 📂 โครงสร้างโฟลเดอร์เทมเพลต
```text
glossary_tool_template/
│
├── README.md                      <-- คู่มือนี้
├── TrilingualExtractor_Prompt.txt <-- พรอมต์สกัดภาษาสำหรับ AI (System & User prompts)
├── aggregate_all.py               <-- [ขั้นที่ 2] รวมไฟล์ JSON จาก raw_extractions/
├── generate_final_glossary.py     <-- [ขั้นที่ 3] Merge + UID + Relations + ส่งออก
├── raw_extractions/               <-- ใส่ผลสกัดดิบทีละตอน (ch001.json, ch002.json, ...)
└── output/                        <-- ผลลัพธ์สุดท้าย (glossary.json, glossary.md)
```

---

## 🛠️ ขั้นตอนการรันระบบ (The 3-Step Pipeline)

### ขั้นตอนที่ 1: สกัดคำศัพท์รายตอนด้วย AI (Extract)
ให้ใช้คู่มือและโครงสร้างพรอมต์จากไฟล์ **TrilingualExtractor_Prompt.txt** ไปป้อนใน AI CLI หรือ AI Web Chat:
1. ตั้งค่าระบบ (System Instructions) ด้วยคำสั่งในหัวข้อ **Specialized Glossary Extraction Agent**
2. ส่งเนื้อหาบทนิยายทั้ง 3 เวอร์ชัน (เกาหลี Raw, อังกฤษ Clean, ไทย Clean) ในตอนนั้นให้ AI อ่าน
3. ส่งคำสั่งด้วย **User Prompt Template** เพื่อสกัดข้อมูล
4. เมื่อ AI ตอบข้อมูลกลับมาในรูปแบบ JSON ในบล็อก ` ```json ` ให้เซฟผลลัพธ์นั้นเป็นไฟล์ `.json` เช่น `ch001.json`, `ch002.json` ไปไว้ในโฟลเดอร์ `raw_extractions/`

---

### ขั้นตอนที่ 2: ควบรวมผลลัพธ์ดิบรายตอน (Aggregate)
เมื่อสะสมไฟล์ผลสกัดดิบในโฟลเดอร์ `raw_extractions/` ครบจำนวนตอนที่ต้องการแล้ว ให้รันสคริปต์ `aggregate_all.py` ในคอมพิวเตอร์ของคุณ:
```bash
python aggregate_all.py
```
*สคริปต์จะรวมไฟล์ในโฟลเดอร์ `raw_extractions` และเขียนไฟล์ `subagent_status.json` ขึ้นมา*

---

### ขั้นตอนที่ 3: สรุปคลังศัพท์และสร้างเอกสารผลลัพธ์ (Consolidate & Format)
รันสคริปต์ `generate_final_glossary.py` เพื่อล้างข้อมูลและส่งออกแบบฟอร์แมตมาตรฐาน:
```bash
python generate_final_glossary.py
```
*สคริปต์จะทำการสร้างไฟล์ `glossary.json` (ฐานข้อมูลสำหรับป้อน AI แปลภาษา) และ `glossary.md` (สำหรับมนุษย์เปิดอ่าน/แก้ไข) ไว้ที่โฟลเดอร์ `output/`*

---

## 💡 วิธีตั้งค่าสำหรับนิยายเรื่องใหม่ (Customization)

เพื่อให้ได้ผลลัพธ์คลังคำศัพท์ที่ไร้ที่ติ คุณสามารถเปิดไฟล์ `generate_final_glossary.py` ขึ้นมาเพื่อแก้ไขส่วนตั้งค่าเหล่านี้:

1. **`nomenclature_overrides` (จัดระเบียบคำแปลหลัก):**
   ใส่คำศัพท์ที่คุณต้องการกำหนดทับด้วยมาตรฐาน เพื่อให้สะกดเหมือนเดิมทุกที่ เช่น:
   ```python
   nomenclature_overrides = {
       "화무기": {
           "thai_version": "ฮวามูคี",
           "english_version": "Hwa Mugi"
       }
   }
   ```
2. **`canonical_keys` (การยุบชื่อตัวตนที่ซ้ำซ้อน):**
   ปัญหากระบวนการแปลมักจะสะกดชื่อตัวละครหลากหลายรูปแบบ (เช่น "คุณชายรอง", "อีกงจา", "อี공자" ทั้งหมดคือคนเดียวกัน) ให้จับคู่เข้าหาคีย์หลัก:
   ```python
   canonical_keys = {
       "이 공자": "검무극",
       "이공자": "검무극",
       "คุณชายอี": "검무극"
   }
   ```
3. **`manual_chapters` (ชุดข้อมูลเสริมความแม่นยำ):**
   หากมีตอนไหนที่กระบวนการสกัดพลาดหรือคุณอยากแต่งเติมข้อมูลเพิ่มด้วยตนเอง สามารถนำมาใส่ในดิกชันนารีนี้ได้โดยระบุเลขบท

4. **`entity_relations` (Knowledge Graph — ความสัมพันธ์ระหว่าง Entity):**
   กำหนดความสัมพันธ์ระหว่างตัวละคร สังกัด และความเกี่ยวข้อง เพื่อสร้างกราฟความรู้:
   ```python
   entity_relations = {
       "검무극(劍無極)": {
           "faction": "천마신교(天魔神敎)",
           "associated_entities": ["이안(李安)", "화무기(華武技)"]
       }
   }
   ```
   ระบบจะ resolve ชื่อภาษาเกาหลีเป็น `uid` ให้โดยอัตโนมัติ

## 🧬 Schema ข้อมูล

แต่ละ entity ใน `glossary.json` มีโครงสร้างดังนี้:
```json
{
  "uid": "char_geom_mugeuk_001",
  "category": "Character",
  "korean_original": "검무극(劍無極)",
  "english_version": "Geom Mugeuk",
  "thai_version": "กอมมูกึก",
  "aliases": {
    "titles": ["บุตรแห่งกระบี่เทพ"],
    "mis_translations": [],
    "other_names": ["Geom Mu-geuk"]
  },
  "description": { "en": "...", "th": "..." },
  "source_chapters": [1, 2, 11],
  "faction_id": "org_heavenly_demon_divine_sect_007",
  "associated_entities": ["char_lee_ahn_010"]
}
```
