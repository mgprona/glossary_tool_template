import os
import json
import re
import sys

try:
    from models import RawGlossaryEntry, ChapterExtraction, ValidationReport
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    print("[WARN] pydantic not installed. Install with: pip install pydantic")
    print("[WARN] Continuing without validation...")


def validate_entry(entry: dict, ch_num: int) -> list[str]:
    errors = []
    if not HAS_PYDANTIC:
        return errors

    try:
        RawGlossaryEntry(**entry)
    except Exception as e:
        errors.append(f"ch{ch_num:03d} [{entry.get('korean_original', '???')[:30]}]: {e}")
    return errors


def aggregate_local_jsons():
    raw_dir = "./raw_extractions"
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir)
        print(f"Created '{raw_dir}' folder. Place raw chapter JSON extraction files there.")
        return {}

    results = {}
    validation_errors = []
    chapter_reports = []

    for filename in sorted(os.listdir(raw_dir)):
        if not filename.endswith(".json"):
            continue

        match = re.search(r"ch(\d+)", filename, re.IGNORECASE)
        if not match:
            continue

        ch_num = int(match.group(1))
        ch_key = f"ch{ch_num:03d}"
        file_path = os.path.join(raw_dir, filename)

        chapter_total = 0
        chapter_valid = 0
        chapter_errors = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                chapter_total = len(data)
                for entry in data:
                    errs = validate_entry(entry, ch_num)
                    if errs:
                        chapter_errors.extend(errs)
                    else:
                        chapter_valid += 1
            else:
                chapter_errors.append(f"ch{ch_key}: expected JSON array, got {type(data).__name__}")

        except json.JSONDecodeError as e:
            chapter_errors.append(f"ch{ch_key}: JSON parse error: {e}")
        except Exception as e:
            chapter_errors.append(f"ch{ch_key}: {e}")

        validation_errors.extend(chapter_errors)
        chapter_reports.append(ChapterExtraction(
            chapter_num=ch_num,
            total_entries=chapter_total,
            valid_entries=chapter_valid,
            invalid_entries=chapter_total - chapter_valid,
            errors=chapter_errors,
        ))

        results[ch_key] = {
            "folder": "local",
            "data": data if isinstance(data, list) else [],
            "error": None if not chapter_errors else chapter_errors[0],
            "validation": {
                "total": chapter_total,
                "valid": chapter_valid,
                "invalid": chapter_total - chapter_valid,
            }
        }

    # Build validation report
    report = ValidationReport(
        total_chapters=len(chapter_reports),
        total_entries=sum(r.total_entries for r in chapter_reports),
        valid_entries=sum(r.valid_entries for r in chapter_reports),
        invalid_entries=sum(r.invalid_entries for r in chapter_reports),
        chapters_with_errors=sum(1 for r in chapter_reports if r.errors),
        chapter_details=chapter_reports,
    )

    # Print summary
    print(f"\n{'='*50}")
    print(f"  AGGREGATION + VALIDATION REPORT")
    print(f"{'='*50}")
    print(f"  Chapters processed:  {report.total_chapters}")
    print(f"  Total entries:       {report.total_entries}")
    print(f"  Valid entries:       {report.valid_entries}")
    print(f"  Invalid entries:     {report.invalid_entries}")
    print(f"  Chapters w/ errors:  {report.chapters_with_errors}")
    print(f"  Validation rate:     {report.success_rate}%")
    print(f"{'='*50}")

    if validation_errors:
        print(f"\n  VALIDATION ERRORS ({len(validation_errors)}):")
        for err in validation_errors[:20]:
            print(f"    - {err}")
        if len(validation_errors) > 20:
            print(f"    ... and {len(validation_errors) - 20} more errors")
    else:
        print(f"\n  [OK] All entries passed validation.")

    # Save validation report
    os.makedirs("output", exist_ok=True)
    with open("output/validation_report.json", "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"\n  Validation report saved: output/validation_report.json")

    return results


if __name__ == "__main__":
    extracted = aggregate_local_jsons()

    # Write to status file
    with open("subagent_status.json", "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)
    print("Saved aggregation to 'subagent_status.json'")
