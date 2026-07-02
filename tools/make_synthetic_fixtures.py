#!/usr/bin/env python3
"""Regenerate the Deltarune test fixtures as fully SYNTHETIC saves.

The originals came from a real save corpus and carried a real player's name.
These reproduce the same evidential shape (layout length, the corroborated
line map, the same salient values the tests assert) with nothing personal:
the player is TESTER. Run from the repo root; writes tests/fixtures/.
"""
from pathlib import Path

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
N = 10318   # the corroborated v1.07-era Chapter 1 layout


def make_save(name, party, dollars, jevil, room, time):
    lines = ["0"] * N
    lines[0] = name
    lines[7], lines[8], lines[9] = str(party[0]), str(party[1]), str(party[2])
    lines[10] = str(dollars)
    lines[558] = str(jevil)
    lines[10316] = str(room)
    lines[10317] = str(time)
    return "\n".join(lines)


def main():
    (FIX / "filech1_0_early").write_text(
        make_save("TESTER", (1, 3, 0), 63, 0, 49, 131655))
    (FIX / "filech1_0_completed").write_text(
        make_save("TESTER", (1, 2, 3), 3000, 2, 126, 831611))
    (FIX / "dr_uraboss.ini").write_text(
        '[G0]\nName="TESTER"\nLevel="1.000000"\nLove="1.000000"\n'
        'Time="778018.000000"\nRoom="403.000000"\nInitLang="0.000000"\n'
        'UraBoss="2.000000"\n')
    print("synthetic fixtures written")


if __name__ == "__main__":
    main()
