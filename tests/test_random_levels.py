"""ทดสอบไฟล์ด่านสุ่มใน random_levels/ ทั้งหมด

รัน:  python tests/test_random_levels.py
หรือ: python -m pytest tests/test_random_levels.py
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as C
from obstacle import Obstacle
from generate_random_levels import analyze_level_paths
import json

RANDOM_DIR = Path(__file__).resolve().parent.parent / "random_levels"


def test_random_levels_exist():
    files = list(RANDOM_DIR.glob("level*.json"))
    assert len(files) == 10, f"Expected 10 level files, found {len(files)}"


def test_random_levels_structure_and_3stars():
    """ตรวจว่าทุกด่านใน random_levels:
    1. ของเรียงตามแกน Z ถูกต้อง
    2. สิ่งกีดขวางไม่กว้างเกินครึ่งถนน (หลบได้เสมอ)
    3. สามารถเล่นจนจบและได้ 3 ดาวได้จริง
    """
    files = sorted(RANDOM_DIR.glob("level*.json"), key=lambda p: int("".join(c for c in p.stem if c.isdigit())))
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        assert data["start_count"] > 0, f"{f.name}: start_count must be > 0"
        assert data["speed"] > 0, f"{f.name}: speed must be > 0"
        assert data["finish_z"] > 0, f"{f.name}: finish_z must be > 0"

        objs = data["objects"]
        zs = [o["z"] for o in objs]
        assert zs == sorted(zs), f"{f.name}: objects must be sorted by Z"
        assert zs[-1] < data["finish_z"], f"{f.name}: all objects must be before finish_z"

        for o in objs:
            if o["type"] == "obstacle":
                assert o["width"] <= C.ROAD_HALF_W, f"{f.name}: obstacle width too wide ({o['width']})"
                assert abs(o["x"]) <= C.ROAD_HALF_W, f"{f.name}: obstacle x out of bounds"

        # Check path feasibility and 3-star capability
        analysis = analyze_level_paths(data)
        assert analysis["is_3star_possible"], f"{f.name}: 3 stars is mathematically IMPOSSIBLE!"
        assert analysis["best_count"] > 0, f"{f.name}: No surviving paths to the finish line!"


if __name__ == "__main__":
    print("Running tests on random_levels...")
    test_random_levels_exist()
    test_random_levels_structure_and_3stars()
    print("All tests passed successfully! All 10 random levels are valid and 3-star achievable.")
