"""ci.yaml 触发方式守卫。

背景：日常用 GitHub Desktop 直接把提交同步到 main，`ci.yaml` 挂 `push: main`
会让每次同步都在 Actions 列表里多出一条 `CI/CD Pipeline`；而主干没有 PR 流程，
这条 run 只会把噪声列表刷长（真出问题还得看日志才知道），故改成只监听 PR，
质量门禁由本地 `uv run quick-check` / `uv run check --skip-hook-install` 承担。

这里锁住"只监听 pull_request、不监听 push"这一条，防止有人顺手把 push 加回来。
"""

import re
from pathlib import Path

import yaml

CI_WORKFLOW = Path(".github/workflows/ci.yaml")


def _ci() -> dict:
    # PyYAML 会把裸 `on` 解析成布尔 True，这里统一取回来。
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def test_ci_workflow_does_not_run_on_push():
    """push 到 main 不再触发 CI：GitHub Desktop 每次同步都会多出一条 run。"""
    triggers = _ci()[True] if True in _ci() else _ci()["on"]

    assert "push" not in triggers, (
        "ci.yaml 不应有 push 触发：GitHub Desktop 每次同步到 main 都会产生一条 "
        "CI/CD Pipeline run。质量门禁改为 PR + 本地 uv run check --skip-hook-install。"
    )


def test_ci_workflow_still_runs_on_pull_request():
    """PR 门禁必须保留，否则 Windows 兼容性与 PyInstaller 冒烟构建彻底失守。"""
    triggers = _ci()[True] if True in _ci() else _ci()["on"]

    assert "pull_request" in triggers, "ci.yaml 必须保留 pull_request 触发"
    assert triggers["pull_request"]["branches"] == ["main"], "PR 门禁应只针对 main"


def test_ci_quality_gates_are_preserved():
    """去掉 push 触发不等于去掉门禁：ruff / mypy / pytest 三个核心步骤必须还在。"""
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    for command in ("ruff format --check", "ruff check", "mypy mdcx/", "pytest tests/"):
        assert command in text, f"ci.yaml 缺少质量门禁步骤：{command}"


def test_ci_classify_step_no_longer_needs_push_event_base():
    """改动分类的 BASE_SHA 仍可保留 push 兜底分支（无害），但不允许出现 `on: push`。"""
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert not re.search(r"(?m)^\s{2}push:\s*$", text), "ci.yaml 顶层出现 push 触发块"
