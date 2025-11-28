import json
from datetime import datetime
from pathlib import Path

if __name__ == "__main__":
    with open("data/analysis.json") as f:
        analysis = json.load(f)

    total = analysis["total_clearances"]
    text = f"""# Medirule Weekly FDA 510(k) Report

Week of 2025-11-16 ~ 2025-11-22

- Total clearances: {total}

(추가 내용은 나중에 채워 넣기)
"""

    Path("newsletters").mkdir(exist_ok=True)
    fn = Path("newsletters") / f"newsletter_{datetime.now().strftime('%Y%m%d')}.md"
    fn.write_text(text, encoding="utf-8")
    print("saved", fn)
