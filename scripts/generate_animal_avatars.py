#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Callable

SVG_SIZE = 128
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "services" / "gateway_api" / "app" / "web" / "animal_avatars"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

Group = tuple[str, list[tuple[str, str]], str]

GROUPS: list[Group] = [
    ("cat", [("cat", "#d97706"), ("tiger", "#ea580c"), ("leopard", "#b45309"), ("lynx", "#a16207"), ("cheetah", "#c2410c")], "cat"),
    ("dog", [("dog", "#8b5e34"), ("wolf", "#6b7280"), ("husky", "#64748b"), ("coyote", "#9a6b3c"), ("dingo", "#c08552")], "dog"),
    ("rabbit", [("rabbit", "#9ca3af"), ("hare", "#b08968"), ("pika", "#8b7f72"), ("jackrabbit", "#a16207"), ("angora", "#94a3b8")], "rabbit"),
    ("bear", [("brown_bear", "#7c4a21"), ("black_bear", "#1f2937"), ("polar_bear", "#94a3b8"), ("panda", "#111827"), ("koala", "#6b7280")], "bear"),
    ("fox", [("red_fox", "#ea580c"), ("fennec", "#d4a373"), ("arctic_fox", "#94a3b8"), ("raccoon", "#4b5563"), ("red_panda", "#c2410c")], "fox"),
    ("lion", [("lion", "#b7791f"), ("cougar", "#a16207"), ("jaguar", "#92400e"), ("hyena", "#9a6b3c"), ("boar", "#7c5a3a")], "lion"),
    ("bird", [("sparrow", "#8b6f47"), ("robin", "#b45309"), ("swallow", "#334155"), ("eagle", "#6b7280"), ("falcon", "#4b5563")], "bird"),
    ("owl", [("owl", "#6b4f3a"), ("snowy_owl", "#94a3b8"), ("barn_owl", "#a16207"), ("crow", "#1f2937"), ("raven", "#111827")], "owl"),
    ("penguin", [("penguin", "#1f2937"), ("puffin", "#334155"), ("auk", "#475569"), ("seagull", "#64748b"), ("albatross", "#94a3b8")], "penguin"),
    ("duck", [("duck", "#b45309"), ("goose", "#9ca3af"), ("swan", "#94a3b8"), ("flamingo", "#db2777"), ("parrot", "#16a34a")], "duck"),
    ("fish", [("goldfish", "#f59e0b"), ("clownfish", "#f97316"), ("tuna", "#64748b"), ("salmon", "#fb7185"), ("shark", "#6b7280")], "fish"),
    ("frog", [("frog", "#16a34a"), ("toad", "#65a30d"), ("newt", "#b45309"), ("salamander", "#ea580c"), ("gecko", "#22c55e")], "frog"),
    ("turtle", [("turtle", "#15803d"), ("tortoise", "#8b5a2b"), ("crocodile", "#3f6212"), ("alligator", "#4d7c0f"), ("lizard", "#65a30d")], "turtle"),
    ("elephant", [("elephant", "#64748b"), ("mammoth", "#7c5a4b"), ("rhino", "#6b7280"), ("hippo", "#52525b"), ("tapir", "#3f3f46")], "elephant"),
    ("monkey", [("monkey", "#8b5a2b"), ("gorilla", "#374151"), ("chimpanzee", "#6b4f3a"), ("orangutan", "#c2410c"), ("lemur", "#6b7280")], "monkey"),
    ("pig", [("pig", "#ec4899"), ("wild_boar", "#7c5a3a"), ("peccary", "#8b6f47"), ("hamster", "#d4a373"), ("guinea_pig", "#a16207")], "pig"),
    ("cow", [("cow", "#4b5563"), ("yak", "#374151"), ("buffalo", "#6b4f3a"), ("bison", "#7c4a21"), ("goat", "#9ca3af")], "cow"),
    ("deer", [("deer", "#8b5a2b"), ("elk", "#7c4a21"), ("moose", "#6b3f1d"), ("reindeer", "#9a6b3c"), ("antelope", "#b08968")], "deer"),
    ("horse", [("horse", "#7c4a21"), ("zebra", "#1f2937"), ("donkey", "#6b7280"), ("mule", "#7c6a58"), ("camel", "#b08968")], "horse"),
    ("seal", [("seal", "#64748b"), ("walrus", "#6b7280"), ("otter", "#8b5a2b"), ("beaver", "#6b4f3a"), ("platypus", "#7c6a58")], "seal"),
]


def line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" />'


def circle(cx: float, cy: float, r: float) -> str:
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" />'


def ellipse(cx: float, cy: float, rx: float, ry: float, rotate_deg: float = 0.0) -> str:
    if abs(rotate_deg) < 0.01:
        return f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" />'
    return (
        f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" '
        f'transform="rotate({rotate_deg:.2f} {cx:.2f} {cy:.2f})" />'
    )


def poly(points: list[tuple[float, float]]) -> str:
    joined = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polygon points="{joined}" />'


def face(rng: random.Random) -> list[str]:
    eye_dx = rng.uniform(10.0, 14.0)
    eye_y = rng.uniform(70.0, 76.0)
    smile_y = rng.uniform(84.0, 90.0)
    return [
        line(64.0 - eye_dx - 2.5, eye_y, 64.0 - eye_dx + 2.5, eye_y),
        line(64.0 + eye_dx - 2.5, eye_y, 64.0 + eye_dx + 2.5, eye_y),
        f'<path d="M52.00 {smile_y:.2f} Q64.00 {smile_y + 8.0:.2f} 76.00 {smile_y:.2f}" />',
    ]


def tpl_cat(rng: random.Random) -> list[str]:
    ear_top = rng.uniform(23.0, 28.0)
    parts = [circle(64, 72, 31), poly([(42, 50), (53, ear_top), (63, 49)]), poly([(86, 50), (75, ear_top), (65, 49)])]
    parts.extend(face(rng))
    parts.extend([line(44, 84, 32, 82), line(44, 88, 31, 90), line(84, 84, 96, 82), line(84, 88, 97, 90)])
    return parts


def tpl_dog(rng: random.Random) -> list[str]:
    ear_len = rng.uniform(14.0, 19.0)
    parts = [circle(64, 72, 30), ellipse(39, 67, 11, ear_len), ellipse(89, 67, 11, ear_len), ellipse(64, 84, 11, 7)]
    parts.extend(face(rng))
    return parts


def tpl_rabbit(rng: random.Random) -> list[str]:
    tilt = rng.uniform(8.0, 13.0)
    parts = [circle(64, 78, 25), ellipse(52, 42, 8, 24, -tilt), ellipse(76, 42, 8, 24, tilt)]
    parts.extend(face(rng))
    return parts


def tpl_bear(rng: random.Random) -> list[str]:
    parts = [circle(64, 74, 29), circle(44, 52, 10), circle(84, 52, 10), ellipse(64, 84, 10, 7)]
    parts.extend(face(rng))
    return parts


def tpl_fox(rng: random.Random) -> list[str]:
    chin = rng.uniform(99.0, 103.0)
    parts = [poly([(36, 70), (44, 50), (55, 41), (73, 41), (84, 50), (92, 70), (64, chin)]), poly([(45, 48), (54, 24), (61, 47)]), poly([(83, 48), (74, 24), (67, 47)])]
    parts.extend(face(rng))
    return parts


def tpl_lion(rng: random.Random) -> list[str]:
    parts = [circle(64, 73, 35), circle(64, 73, 24)]
    parts.extend(face(rng))
    parts.append(ellipse(64, 86, 9, 6))
    return parts


def tpl_bird(rng: random.Random) -> list[str]:
    parts = [circle(60, 72, 26), poly([(86, 70), (103, 76), (86, 82)]), line(44, 92, 76, 92)]
    parts.extend(face(rng))
    parts.append(line(55, 47, 63, 39))
    return parts


def tpl_owl(rng: random.Random) -> list[str]:
    parts = [circle(64, 76, 30), circle(52, 72, 9), circle(76, 72, 9), line(64, 80, 64, 92)]
    parts.extend(face(rng))
    return parts


def tpl_penguin(rng: random.Random) -> list[str]:
    parts = [ellipse(64, 80, 27, 33), circle(64, 60, 20), poly([(64, 72), (72, 76), (64, 80), (56, 76)]), line(52, 105, 57, 110), line(76, 105, 71, 110)]
    parts.extend(face(rng))
    return parts


def tpl_duck(rng: random.Random) -> list[str]:
    parts = [circle(60, 72, 25), ellipse(86, 78, 14, 7), line(40, 93, 78, 93)]
    parts.extend(face(rng))
    return parts


def tpl_fish(rng: random.Random) -> list[str]:
    parts = [ellipse(60, 72, 28, 19), poly([(88, 72), (108, 58), (108, 86)]), poly([(60, 61), (70, 48), (80, 62)]), circle(48, 70, 2.8)]
    parts.append(line(40, 78, 76, 78))
    return parts


def tpl_frog(rng: random.Random) -> list[str]:
    parts = [circle(64, 76, 28), circle(50, 52, 8), circle(78, 52, 8)]
    parts.extend(face(rng))
    return parts


def tpl_turtle(rng: random.Random) -> list[str]:
    parts = [circle(64, 74, 28), circle(92, 74, 8), line(40, 56, 32, 50), line(40, 92, 32, 98), line(88, 56, 96, 50), line(88, 92, 96, 98), circle(64, 74, 12)]
    parts.extend(face(rng))
    return parts


def tpl_elephant(rng: random.Random) -> list[str]:
    trunk_end = rng.uniform(100.0, 106.0)
    parts = [circle(64, 70, 26), circle(44, 70, 14), circle(84, 70, 14), f'<path d="M64 78 Q64 92 64 {trunk_end:.2f} Q68 {trunk_end + 4:.2f} 74 {trunk_end - 2:.2f}" />']
    parts.extend(face(rng))
    return parts


def tpl_monkey(rng: random.Random) -> list[str]:
    parts = [circle(64, 74, 27), circle(40, 72, 10), circle(88, 72, 10), ellipse(64, 84, 12, 8)]
    parts.extend(face(rng))
    return parts


def tpl_pig(rng: random.Random) -> list[str]:
    parts = [circle(64, 74, 29), poly([(48, 51), (56, 40), (60, 54)]), poly([(80, 51), (72, 40), (68, 54)]), ellipse(64, 84, 12, 8), line(60, 84, 60, 86), line(68, 84, 68, 86)]
    parts.extend(face(rng))
    return parts


def tpl_cow(rng: random.Random) -> list[str]:
    parts = [circle(64, 74, 29), poly([(46, 50), (40, 44), (48, 42)]), poly([(82, 50), (88, 44), (80, 42)]), ellipse(64, 85, 13, 8), line(58, 85, 58, 87), line(70, 85, 70, 87)]
    parts.extend(face(rng))
    return parts


def tpl_deer(rng: random.Random) -> list[str]:
    parts = [circle(64, 76, 27), line(50, 50, 45, 35), line(50, 50, 56, 37), line(78, 50, 83, 35), line(78, 50, 72, 37)]
    parts.extend(face(rng))
    return parts


def tpl_horse(rng: random.Random) -> list[str]:
    parts = [ellipse(64, 76, 24, 31), line(52, 52, 45, 44), line(48, 58, 41, 52), line(56, 49, 50, 39), ellipse(64, 88, 9, 6)]
    parts.extend(face(rng))
    return parts


def tpl_seal(rng: random.Random) -> list[str]:
    parts = [ellipse(64, 77, 31, 24), circle(52, 74, 2.8), circle(76, 74, 2.8), ellipse(64, 84, 8, 5), line(47, 85, 33, 83), line(47, 89, 33, 91), line(81, 85, 95, 83), line(81, 89, 95, 91)]
    parts.extend(face(rng))
    return parts


TEMPLATES: dict[str, Callable[[random.Random], list[str]]] = {
    "cat": tpl_cat,
    "dog": tpl_dog,
    "rabbit": tpl_rabbit,
    "bear": tpl_bear,
    "fox": tpl_fox,
    "lion": tpl_lion,
    "bird": tpl_bird,
    "owl": tpl_owl,
    "penguin": tpl_penguin,
    "duck": tpl_duck,
    "fish": tpl_fish,
    "frog": tpl_frog,
    "turtle": tpl_turtle,
    "elephant": tpl_elephant,
    "monkey": tpl_monkey,
    "pig": tpl_pig,
    "cow": tpl_cow,
    "deer": tpl_deer,
    "horse": tpl_horse,
    "seal": tpl_seal,
}


def to_svg(parts: list[str], color: str) -> str:
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_SIZE}" height="{SVG_SIZE}" '
        f'viewBox="0 0 {SVG_SIZE} {SVG_SIZE}" role="img" aria-label="animal-avatar">'
        '<rect x="0" y="0" width="128" height="128" rx="18" fill="white" />'
        f'<g fill="none" stroke="{color}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round">'
    )
    tail = "</g></svg>"
    return head + "".join(parts) + tail


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for file in OUTPUT_DIR.glob("*.svg"):
        file.unlink()

    manifest: list[dict[str, str | int]] = []
    index = 1
    for group_name, animals, template_name in GROUPS:
        renderer = TEMPLATES[template_name]
        for animal_name, color in animals:
            rng = random.Random(index * 7919)
            parts = renderer(rng)
            filename = f"avatar_{index:03d}_{animal_name}.svg"
            content = to_svg(parts, color)
            (OUTPUT_DIR / filename).write_text(content + "\n", encoding="utf-8")
            manifest.append(
                {
                    "index": index,
                    "group": group_name,
                    "animal": animal_name,
                    "template": template_name,
                    "color": color,
                    "file": filename,
                }
            )
            index += 1

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"generated={index - 1} output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
