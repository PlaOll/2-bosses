"""ทดสอบ logic ที่ไม่ต้องเปิดหน้าต่าง   [เจ้าของ: C]

รัน:  python -m pytest      (หรือ  python tests/test_logic.py  ถ้าไม่มี pytest)
ทำไมต้องมี: ก่อน merge เข้า main รันไฟล์นี้ ถ้าใครแก้สูตรพัง จะรู้ทันที
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gate import Gate
from crowd import Crowd
from obstacle import Obstacle
from enemy import EnemyGroup
import config as C
import scores
from gate import GatePair
from level import load_level, list_levels, best_count, build_object


def test_gate_ops():
    assert Gate(0, 1, "+", 20).apply(10) == 30
    assert Gate(0, 1, "x", 3).apply(10) == 30
    assert Gate(0, 1, "/", 3).apply(10) == 3      # ปัดลง
    assert Gate(0, 1, "-", 10).apply(4) == 0      # ไม่ติดลบ


def test_obstacle_hit_and_miss():
    # กติกาของ B (branch dew): คนที่อยู่ในความกว้างของสิ่งกีดขวางหายหมด, damage ไม่ถูกใช้แล้ว
    crowd = Crowd(20)
    crowd.x = 75
    Obstacle(-75, 100, 150, 5).on_reach(crowd)    # อยู่คนละฝั่ง ไม่โดน
    assert crowd.count == 20
    crowd.x = -75
    Obstacle(-75, 100, 150, 5).on_reach(crowd)    # ทั้งก้อนอยู่ในช่วงพอดี โดนหมด
    assert crowd.count == 0


def test_enemy_fight():
    crowd = Crowd(50)
    EnemyGroup(100, 40).on_reach(crowd)
    assert crowd.count == 10


def test_level1_loads_sorted():
    level = load_level("level1.json")
    zs = [o.z for o in level.objects]
    assert zs == sorted(zs)
    assert level.finish_z > zs[-1]


# ---------- ประตู: กรณีขอบ ----------

def test_gate_invalid():
    for bad in (("?", 1), ("/", 0)):
        try:
            Gate(0, 1, *bad)
        except ValueError:
            continue
        raise AssertionError(f"Gate{bad} ควร raise ValueError")


def test_gate_good_and_label():
    assert Gate(0, 1, "+", 5).is_good() and Gate(0, 1, "x", 2).is_good()
    assert not Gate(0, 1, "-", 5).is_good() and not Gate(0, 1, "/", 2).is_good()
    assert Gate(0, 1, "x", 3).label() == "×3"
    assert Gate(0, 1, "/", 2).label() == "÷2"


def test_gate_pair_picks_side():
    crowd = Crowd(10)
    crowd.x = -50                              # ฝั่งซ้าย
    GatePair(100, ("+", 5), ("x", 10)).on_reach(crowd)
    assert crowd.count == 15
    crowd.x = 50                               # ฝั่งขวา
    pair = GatePair(100, ("+", 5), ("x", 10))
    pair.on_reach(crowd)
    assert crowd.count == 150 and pair.used
    crowd.x = 0                                # ตรงกลางพอดี นับเป็นฝั่งขวา (x_min <= x)
    GatePair(100, ("-", 100), ("+", 1)).on_reach(crowd)
    assert crowd.count == 151


# ---------- ศัตรู ----------

def test_enemy_bigger_than_crowd():
    crowd = Crowd(10)
    enemy = EnemyGroup(100, 25)
    enemy.on_reach(crowd)
    assert crowd.count == 0 and enemy.count == 15 and enemy.used


# ---------- ไฟล์ด่าน ----------

def test_list_levels_numeric_order():
    files = list_levels()
    assert files[0] == "level1.json"
    nums = [int("".join(ch for ch in f if ch.isdigit())) for f in files]
    assert nums == sorted(nums)


def test_build_object_unknown_type():
    try:
        build_object({"type": "dragon", "z": 1})
    except ValueError:
        return
    raise AssertionError("type ที่ไม่รู้จักควร raise ValueError")


def test_all_levels_valid():
    """ทุกด่าน: โหลดได้, เรียงตาม z, ของอยู่บนถนนก่อนเส้นชัย, หลบสิ่งกีดขวางได้, ชนะได้จริง"""
    for filename in list_levels():
        level = load_level(filename)
        zs = [o.z for o in level.objects]
        assert zs == sorted(zs), filename
        assert level.start_count > 0 and level.speed > 0, filename
        assert zs and 0 < zs[0] and zs[-1] < level.finish_z, filename
        for obj in level.objects:
            if isinstance(obj, Obstacle):
                # กว้างไม่เกินครึ่งถนน = มีช่องให้หลบเสมอ (สิ่งกีดขวางลบทุกคนที่โดน)
                assert obj.width <= C.ROAD_HALF_W, f"{filename}: obstacle z={obj.z} กว้างเกิน"
                assert abs(obj.x) <= C.ROAD_HALF_W, filename
        assert best_count(level) > 0, f"{filename}: เลือกประตูดีที่สุดแล้วยังแพ้"


def test_levels_get_harder():
    """ด่านหลังๆ วิ่งเร็วขึ้น (หรือเท่าเดิม) และยาวขึ้น (หรือเท่าเดิม)"""
    levels = [load_level(f) for f in list_levels()]
    for a, b in zip(levels, levels[1:]):
        assert b.speed >= a.speed or b.finish_z > a.finish_z, f"{b.name} ง่ายกว่า {a.name}"


def test_best_count_level1():
    # 10 -> +20=30 -> x3=90 -> +35=125 -> x2=250 -> สู้ศัตรู 40 = 210
    assert best_count(load_level("level1.json")) == 210


# ---------- ดาว + high score ----------

def test_stars():
    assert scores.stars(False, 100, 200) == 0
    assert scores.stars(True, 0, 200) == 0
    assert scores.stars(True, 10, 200) == 1
    assert scores.stars(True, 50, 200) == 2
    assert scores.stars(True, 100, 200) == 3
    assert scores.stars(True, 5, 0) == 1        # กันหารศูนย์


def test_highscore_save_and_keep_best(tmp_path=None):
    import tempfile
    folder = Path(tmp_path or tempfile.mkdtemp())
    path = folder / "scores.json"
    assert scores.load_scores(path) == {}                     # ยังไม่มีไฟล์
    assert scores.record("level1.json", 50, 2, path)
    assert not scores.record("level1.json", 30, 1, path)      # แย่กว่าเดิม ไม่ทับ
    assert scores.record("level1.json", 80, 1, path)          # ดีกว่า: คนเพิ่ม แต่ดาวเก็บค่าสูงสุดไว้
    assert scores.load_scores(path)["level1.json"] == {"count": 80, "stars": 2}
    path.write_text("not json{", encoding="utf-8")            # ไฟล์เสีย ต้องไม่ทำเกมพัง
    assert scores.load_scores(path) == {}


def test_unlock_needs_previous_win():
    files = ["level1.json", "level2.json", "level3.json"]
    assert scores.is_unlocked(files, 0, {})                    # ด่านแรกเปิดเสมอ
    assert not scores.is_unlocked(files, 1, {})
    won1 = {"level1.json": {"count": 10, "stars": 1}}
    assert scores.is_unlocked(files, 1, won1)
    assert not scores.is_unlocked(files, 2, won1)              # ข้ามด่านไม่ได้


def test_obstacle_update():
    obs = Obstacle(0, 100, 100, 5)
    init_x = obs.x
    obs.update(0.5)
    assert obs.x != init_x or obs.time_accumulator > 0


def test_scorpion_boss():
    from boss import ScorpionBoss, STATE_IDLE, STATE_TELEGRAPH, STATE_ATTACK
    boss = ScorpionBoss(z=1000, max_hp=1000)
    assert boss.hp == 1000
    crowd = Crowd(10)
    # Boss takes damage from bullets
    boss.trigger_hit(50)
    assert boss.hp == 950
    # Crowd shoots bullets after shoot_interval
    boss.update(boss.shoot_interval + 0.1, crowd)
    assert len(boss.bullets) == 10
    # Update bullets to hit boss
    for _ in range(30):
        boss.update(0.05, crowd)
    assert boss.hp < 950

    # Test boss attack cycle
    boss.state = STATE_IDLE
    boss.state_timer = boss.idle_duration
    boss.update(0.01, crowd)
    assert boss.state == STATE_TELEGRAPH
    assert boss.danger_rect is not None

    boss.state_timer = boss.telegraph_duration
    boss.update(0.01, crowd)
    assert boss.state == STATE_ATTACK


def test_plant_boss():
    from boss import PlantBoss, STATE_IDLE, STATE_TELEGRAPH, STATE_ATTACK
    boss = PlantBoss(z=1000, max_hp=2000)
    assert boss.hp == 2000
    crowd = Crowd(10)
    # Boss takes damage from bullets
    boss.trigger_hit(100)
    assert boss.hp == 1900
    # Crowd shoots bullets after shoot_interval
    boss.update(boss.shoot_interval + 0.1, crowd)
    assert len(boss.bullets) == 10
    # Update bullets to hit boss
    for _ in range(30):
        boss.update(0.05, crowd)
    assert boss.hp < 1900

    # Test boss attack cycle
    boss.state = STATE_IDLE
    boss.state_timer = boss.idle_duration
    boss.update(0.01, crowd)
    assert boss.state == STATE_TELEGRAPH
    assert boss.danger_rect is not None

    boss.state_timer = boss.telegraph_duration
    boss.update(0.01, crowd)
    assert boss.state == STATE_ATTACK


def test_plant_boss_poison_mechanics():
    from boss import PlantBoss, PoisonPool
    boss = PlantBoss(z=1000, max_hp=2000)
    crowd = Crowd(5)
    crowd.x = 0.0
    crowd.z = 740.0

    pool = PoisonPool(x=0.0, z=740.0, duration=6.0, radius_x=60.0, radius_z=40.0)
    assert pool.is_active
    assert pool.contains(0.0, 740.0)
    assert not pool.contains(120.0, 740.0)
    boss.poison_pools.append(pool)

    for p in crowd.people:
        p.dx = 0.0
        p.dz = 0.0
        p.poison_time = 0.0

    # ยืนในบ่อพิษ 0.5 วินาที -> poison_time เพิ่มเป็น 0.5
    boss.update(0.5, crowd)
    for p in crowd.people:
        assert abs(p.poison_time - 0.5) < 1e-4

    # เดินออกจากบ่อพิษ 0.3 วินาที -> poison_time ลดลงเหลือ 0.2
    crowd.x = 200.0
    boss.update(0.3, crowd)
    for p in crowd.people:
        assert abs(p.poison_time - 0.2) < 1e-4

    # เดินกลับเข้าบ่อพิษ 0.3 วินาที -> poison_time สะสมต่อจาก 0.2 เป็น 0.5
    crowd.x = 0.0
    boss.update(0.3, crowd)
    for p in crowd.people:
        assert abs(p.poison_time - 0.5) < 1e-4

    # ยืนต่อเนื่องจนถึง poison_death_time (2.0s) -> ตายทันที
    boss.update(1.6, crowd)
    assert crowd.count == 0


def test_plant_boss_bite_attacks():
    from boss import PlantBoss, ATTACK_FRONT, ATTACK_LEFT, ATTACK_RIGHT
    boss = PlantBoss(z=1000, max_hp=2000)
    for att_type, center_x in [(ATTACK_FRONT, 0.0), (ATTACK_LEFT, -150.0), (ATTACK_RIGHT, 150.0)]:
        boss.attack_mode = "chop"
        boss.attack_type = att_type
        boss.danger_rect = (center_x - 50.0, center_x + 50.0)

        crowd = Crowd(2)
        crowd.people[0].dx = center_x
        crowd.people[1].dx = center_x + 120.0
        boss.execute_attack_damage(crowd)
        assert crowd.count == 1, f"Expected 1 survivor for {att_type}, got {crowd.count}"


def test_plant_boss_max_two_pools():
    from boss import PlantBoss, PoisonPool
    boss = PlantBoss(z=1000, max_hp=2000)
    crowd = Crowd(5)

    # ทดสอบว่าขนาดบ่อพิษเริ่มต้นสอดคล้องกับระยะเดินสุ่มของตัวละคร
    pool_default = PoisonPool(0, 0)
    assert pool_default.radius_x == 34.0
    assert pool_default.radius_z == 30.0

    # จำลองเมื่อมีบ่อพิษ 2 บ่ออยู่แล้ว
    p1 = PoisonPool(0, 740)
    p2 = PoisonPool(50, 740)
    boss.poison_pools = [p1, p2]

    # บอสต้องเปลี่ยนไปใช้งานท่างับกัด (chop) เท่านั้น เพื่อไม่ให้เกิน 2 บ่อ
    for _ in range(10):
        boss.start_attack(0, 740)
        assert boss.attack_mode == "chop"

    # หากมีกระสุนพิษตกลงมาเพิ่ม จำนวนบ่อต้องไม่เกิน 2 บ่อเสมอ
    boss.spits.append(type("MockSpit", (), {
        "alive": False, "target_x": -50, "target_z": 740,
        "update": lambda self, dt: None
    })())
    boss.update(0.016, crowd)
    assert len(boss.poison_pools) <= 2


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
