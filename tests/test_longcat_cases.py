"""test_longcat_cases.py — LongCat-2.0 生成的 dem-terrain-analysis 测试用例（离线）"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))


def _run(args, timeout=15):
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "dem-terrain-analysis.py")] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def test_longcase_help_works():
    out = _run(["--help"])
    assert out.returncode == 0
    # dem-terrain-analysis 是 subcommand 风格
    assert "slope" in out.stdout
    assert "aspect" in out.stdout
    assert "from-place" in out.stdout


def test_longcase_missing_input():
    """缺子命令 → argparse exit 2"""
    out = _run([
        "--output", os.path.join(os.environ.get("TEMP", "/tmp"), "lc_dem.tif"),
    ])
    assert out.returncode == 2
    combined = out.stdout + out.stderr
    assert "invalid choice" in combined or "required" in combined or "the following arguments" in combined


def test_longcase_slope_help():
    out = _run(["slope", "--help"])
    assert out.returncode == 0
    # dem-terrain-analysis slope 子命令用 --input 或 --place
    combined = out.stdout + out.stderr
    assert "--input" in combined or "--place" in combined
    assert "--output" in combined
