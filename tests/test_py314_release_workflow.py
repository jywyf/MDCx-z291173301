"""Python 3.14 发版工作流与 3.13 正式版的隔离守卫（`.github/workflows/build-py314.yml`）。

背景：`build-py314.yml` 手动触发并勾选 `publish` 时会创建一条 3.14 预览 Release，
而 `release.yml`（Python 3.13 正式发版，tag `2*` 触发）继续保留。两条流程共用同一版本号，
靠下面四条约定互不干扰，任何一条被改坏都会伤到 3.13 正式版的发版或客户端自动更新：

1. **tag 命名空间隔离**：预览 tag 为 `py314-<版本号>`，非纯数字。
   `mdcx/base/web.py` 的 `check_version()` 遍历 releases 取第一个 `tag_name.isdigit()`
   的值（`releases?per_page=10`），非纯数字 tag 会被跳过，故预览对自动更新不可见。
2. **不抢 Latest**：预览 Release 显式 `make_latest: false`，仓库 Latest 与文档里的
   `/releases/latest/download/` 链接永远指向 3.13 正式版。
3. **只允许手动发版**：`publish-release` 要求 `workflow_dispatch` + `publish` 勾选。
   否则每次 push main 都抢同一个 `py314-<版本>` tag，官方 tag 推送时两个工作流同时
   `POST /releases` 撞 422，把 3.13 正式发版撞挂。工作流也不得监听 tag 发版。
4. **缺产物不发版**：`build-app` 带 `continue-on-error`，所以 `publish-release` 必须用
   `needs.build-app.result == 'success'` 把关（不能写 `success()`：`needs` 里任一失败腿
   都会让它整体跳过），并在上传前核对四个平台产物齐全——半成品 Release 比不发更糟。

按仓库惯例做文本断言（`tests/` 不引入 yaml 依赖），改工作流后请同步更新本文件。
"""

import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_WORKFLOW = _ROOT / ".github" / "workflows" / "build-py314.yml"

# 一次预览 Release 覆盖的平台资产（macOS 两架构共用一个构建目录，文件名由 build-app 决定）
_ASSET_FILES = (
    "dist/MDCx-aarch64.dmg",
    "dist/MDCx-x86_64.dmg",
    "dist/MDCx.exe",
    "dist/MDCx",
)

_RELEASE_STEP_COUNT = 4


def _workflow() -> str:
    return _WORKFLOW.read_text(encoding="utf-8")


def test_preview_tag_is_prefixed_and_not_digit():
    """预览 Release 的 tag 必须带 `py314-` 前缀，且不得出现纯数字 tag。"""
    text = _workflow()

    assert 'echo "tag=py314-$version" >> "$GITHUB_OUTPUT"' in text, (
        "build-py314.yml 不再把预览 tag 加 py314- 前缀；纯数字 tag 会与 release.yml 的正式版"
        "共用同一命名空间，check_version 会把 3.14 预览当成正式版推给客户端"
    )
    assert "tag: ${{ steps.metadata.outputs.version }}" not in text, (
        "检测到用纯数字版本号当 Release tag；请用 steps.metadata.outputs.tag（py314- 前缀）"
    )
    assert "tag: ${{ steps.metadata.outputs.tag }}" in text, "四个 Create Release 步骤都应引用带前缀的 tag"


def test_preview_release_never_marked_latest():
    """预览 Release 不得抢仓库 Latest 标记，否则文档里的 latest 下载链接会指向预览包。"""
    text = _workflow()
    # 只数真正的配置行（行尾即止），文件头的说明注释里也会出现同样的字样
    explicit_false = len(re.findall(r"(?m)^\s+make_latest: false$", text))

    assert "make_latest: true" not in text, "3.14 预览不得标记为 Latest（Latest 属于 3.13 正式版）"
    assert explicit_false == _RELEASE_STEP_COUNT, (
        f"期望 {_RELEASE_STEP_COUNT} 个 Create Release 步骤都显式写 `make_latest: false`，"
        f"实际 {explicit_false} 个；漏写的那个会走 action 默认值 true 去抢 Latest"
    )


def test_publish_requires_manual_dispatch():
    """发版必须限手动触发，且工作流不得监听 tag 发版。"""
    text = _workflow()
    condition = re.search(r"(?m)^\s{4}if: \$\{\{ (.+) \}\}$", text)

    assert condition is not None, "找不到 publish-release 的 if 条件"
    gate = condition.group(1)
    assert "needs.build-app.result == 'success'" in gate, "发版条件必须核对 build-app 的真实结果"
    assert "github.event_name == 'workflow_dispatch'" in gate, (
        "发版条件必须限定 workflow_dispatch；push main 自动发版会与 release.yml 抢同一个 tag"
    )
    assert "inputs.publish" in gate, "发版条件必须尊重 publish 输入（只想要产物时不应发版）"
    assert re.search(r"(?m)^    tags:\s*$", text) is None, (
        "build-py314.yml 不得监听 tag；纯数字 tag 是 release.yml 正式发版的触发条件"
    )


def test_publish_requires_all_platform_artifacts():
    """上传前必须核对四平台产物齐全，避免发半成品 Release。"""
    text = _workflow()

    assert "- name: Verify all platform assets present" in text, "缺少产物核对步骤"
    verify_idx = text.index("- name: Verify all platform assets present")
    assert verify_idx < text.index("- name: Create Release - macOS (Apple Silicon)"), (
        "产物核对必须在第一个 Create Release 之前"
    )
    for asset in _ASSET_FILES:
        assert f'[ -s {asset} ]' in text, f"产物核对漏了 {asset}"
        assert f"file: {asset}" in text, f"缺少 {asset} 的上传步骤"


def test_release_uploads_are_idempotent():
    """重跑同一 commit 时不得重复上传或改坏已有 Release。"""
    text = _workflow()

    assert text.count("overwrite: true") >= _RELEASE_STEP_COUNT, (
        "Create Release 步骤需要 overwrite: true，重跑时才不会因已存在同名 Release 而失败"
    )
    assert text.count("target_commit: ${{ github.sha }}") == _RELEASE_STEP_COUNT, (
        "预览 tag 应指向本次构建的 commit（target_commit），否则 tag 会落在默认分支上"
    )
    assert text.count("-py314-") >= _RELEASE_STEP_COUNT, "资产名需要带 -py314- 段与 3.13 正式资产区分"
    assert "contents: write" in text, "创建 Release 需要 permissions: contents: write"
