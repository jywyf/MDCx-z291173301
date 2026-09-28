"""全部 GitHub Actions 工作流的 YAML 可解析性与 action 版本守卫。

两件事：

1. **YAML 可解析**：工作流删改（如 2026-09-28 删掉 `build-py313.yml` / `build-windows.yml`
   / `build-linux.yml`）极易让测试里的路径常量悄悄指向已不存在的文件——
   `test_py314_release_workflow.py` 就这么炸过一次（`FileNotFoundError`）。这里对
   `.github/workflows/` 下每个文件做一次 `yaml.safe_load`，删改后当天即红，不必等 CI 或发版。
2. **Node 20 弃用**：`actions/cache@v4` 跑在 Node 20 runtime 上，2025-09-19 起 GitHub
   弃用该 runtime，每次构建都会刷
   `Node.js 20 is deprecated ... being forced to run on Node.js 24: actions/cache@v4`。
   v5 起转 node24、v6 补 ESM 迁移，输入 `path` / `key` / `restore-keys` /
   `fail-on-cache-miss` 全未变。仅自建 runner 需 ≥ 2.327.1，本仓库全为 GitHub 托管 runner。

按仓库惯例不引入新依赖：`yaml` 已是 dev 依赖（`test_ci_workflow_triggers.py` 在用）。
"""

import re
from pathlib import Path

import yaml

_ROOT = Path(__file__).parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"

# actions/cache 的最后一个 Node 20 runtime 版本；v5 起为 node24。
_NODE20_CACHE_MAJOR = 4


def _workflow_files() -> list[Path]:
    files = sorted(_WORKFLOWS.glob("*.y*ml"))
    assert files, f"{_WORKFLOWS} 下没有工作流文件，路径常量是否变了？"
    return files


def test_every_workflow_is_valid_yaml():
    """每个工作流都必须能被 yaml.safe_load 解析（改名/缩进错会当场红）。"""
    for path in _workflow_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{path.name} 解析结果不是映射：{type(data)!r}"
        assert data.get(True) or data.get("on"), f"{path.name} 缺少触发器（`on:` 被当成布尔 True）"
        assert data.get("jobs"), f"{path.name} 缺少 jobs"


def test_no_workflow_pins_node20_actions_cache():
    """不得再出现 `actions/cache@v4`（Node 20 runtime，2025-09-19 弃用）。"""
    offenders: list[str] = []
    for path in _workflow_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.search(r"uses:\s*actions/cache@v?(\d+)", line)
            if match and int(match.group(1)) <= _NODE20_CACHE_MAJOR:
                offenders.append(f"{path.name}: {line.strip()}")
    assert not offenders, "以下工作流仍 pin 着 Node 20 版 actions/cache：\n" + "\n".join(offenders)


def test_actions_cache_pins_are_consistent():
    """全仓库 `actions/cache` 主版本号必须统一，避免同一份 SR 工具缓存被两种 runtime 分裂。"""
    majors: set[int] = set()
    for path in _workflow_files():
        majors.update(int(m) for m in re.findall(r"uses:\s*actions/cache@v?(\d+)", path.read_text(encoding="utf-8")))
    assert len(majors) == 1, f"actions/cache 版本不统一：{sorted(majors)}"
