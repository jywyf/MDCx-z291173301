"""Python 3.14 发版工作流与 `release.yml` 的一致性守卫（`.github/workflows/build-py314.yml`）。

背景：`build-py314.yml` 是 `release.yml`（Python 3.13 正式发版）的 3.14 孪生流程，
两者逐步骤对齐（同样的四平台矩阵、同样的纯数字 tag、同样的资产命名），差别只有四处：
`python-version` 3.14、`UV_PYTHON` 锁 3.14、构建前断言解释器确实是 3.14、
`uv sync --locked` 失败自动回退重新解析。任何一处被改坏都会伤到发版或客户端自动更新：

1. **tag 必须是纯数字**（= `mdcx/consts.py` 的 `LOCAL_VERSION`）：`mdcx/base/web.py` 的
   `check_version()` 遍历 releases 取第一个 `tag_name.isdigit()` 的值（`per_page=10`），
   非纯数字 tag 会被跳过，自动更新就永久失效。故不得回退到早期版本的 `py314-<版本号>`
   预览 tag 方案。
2. **不监听 tag、只手动触发**：tag 推送是 `release.yml` 的触发条件，两者共用纯数字
   命名空间，同一版本号并发发版会同时 `POST /releases` 撞 422。
3. **输入只有 tag 与 prerelease**：平台固定四平台（无 `platforms` 开关）、发版不再有
   `publish` 勾选、relock 回退不再有 true/false 开关（3.14 恒允许回退）。
4. **缺产物不发版**：`build-app` 带 `continue-on-error`，所以 `publish-release` 必须用
   `needs.build-app.result == 'success'` 把关（不能写 `success()`：`needs` 里任一失败腿
   都会让它整体跳过），并在上传前核对四个平台产物齐全——半成品 Release 比不发更糟。

按仓库惯例做文本断言（`tests/` 不引入 yaml 依赖），改工作流后请同步更新本文件。
"""

import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_WORKFLOW = _ROOT / ".github" / "workflows" / "build-py314.yml"
_RELEASE = _ROOT / ".github" / "workflows" / "release.yml"

# 一次 Release 覆盖的平台资产（macOS 两架构共用一个构建目录，文件名由 build-app 决定）
_ASSET_FILES = (
    "dist/MDCx-aarch64.dmg",
    "dist/MDCx-x86_64.dmg",
    "dist/MDCx.exe",
    "dist/MDCx",
)

_RELEASE_STEP_COUNT = 4

# 固定四平台矩阵（与 release.yml 同一套 runner 组合，actions/runner#1985）
_MATRIX_ITEMS = (
    '{"build": "macos", "os": "macos-latest", "arch": "aarch64"}',
    '{"build": "macos", "os": "macos-15-intel", "arch": "x86_64"}',
    '{"build": "windows", "os": "windows-2025", "arch": "x86_64"}',
    '{"build": "linux", "os": "ubuntu-latest", "arch": "x86_64"}',
)


def _workflow() -> str:
    return _WORKFLOW.read_text(encoding="utf-8")


def test_tag_is_plain_numeric_not_py314_prefixed():
    """Release tag 必须是纯数字版本号，不得回退到 `py314-` 前缀。"""
    text = _workflow()

    assert re.search(r"tag=py314-", text) is None, (
        "build-py314.yml 不得给 tag 加 py314- 前缀：非纯数字 tag 会被 check_version 的 "
        "tag_name.isdigit() 跳过，客户端自动更新永久失效"
    )
    # 只查真正的配置行：工作流名/并发组里的 build-py314- 是合法的
    assert re.search(r"(?m)^\s+asset_name:.*py314", text) is None, (
        "资产名不得带 -py314- 段：与 release.yml 共用纯数字 tag 与 `MDCx-<版本>-<平台>-"
        "<架构>-<sha>` 命名，两条流程会更新同一条 Release 的同名资产"
    )
    assert 'echo "tag=$tag" >> "$GITHUB_OUTPUT"' in text, "metadata 步骤应回输出解析出的纯数字 tag"
    assert text.count("tag: ${{ steps.metadata.outputs.tag }}") == _RELEASE_STEP_COUNT, (
        "四个 Create Release 步骤都应引用纯数字 tag"
    )
    assert re.search(r"\^\[0-9\]\+\$", text), "tag 必须做纯数字校验（同 release.yml 的 int(tag) 约束）"


def test_workflow_does_not_listen_to_tags():
    """纯数字 tag 的推送只属于 release.yml；本工作流只手动触发。"""
    text = _workflow()

    assert re.search(r"(?m)^  push:$", text) is None, (
        "build-py314.yml 不得监听 push；tag `2*` 是 release.yml 正式发版的触发条件，"
        "两者对同一版本号并发 POST /releases 会撞 422"
    )
    assert re.search(r"(?m)^    tags:\s*$", text) is None, "build-py314.yml 不得监听 tag"
    assert re.search(r"(?m)^  workflow_dispatch:$", text) is not None, "应保留手动触发入口"


def test_only_tag_and_prerelease_inputs():
    """手动触发只留版本号与 prerelease 两个输入，恒构建四平台、恒允许 relock 回退。"""
    text = _workflow()

    for removed in ("platforms:", "publish:", "allow_relock:"):
        assert removed not in text, f"build-py314.yml 不应有 {removed} 输入"
    for reference in ("inputs.platforms", "inputs.publish", "inputs.allow_relock"):
        assert reference not in text, f"不应再引用 {reference}"
    assert re.search(r"(?m)^      tag:$", text) is not None, "应保留 tag 输入"
    assert re.search(r"(?m)^      prerelease:$", text) is not None, "应保留 prerelease 输入（同 release.yml）"
    assert re.search(r"(?m)^\s+prerelease: \$\{\{ steps\.metadata\.outputs\.prerelease \}\}$", text), (
        "四个 Create Release 步骤都应沿用 metadata 解析出的 prerelease"
    )


def test_matrix_always_builds_all_four_platforms():
    """平台不再可选，矩阵固定四平台且与 release.yml 同一套 runner 组合。"""
    text = _workflow()

    for item in _MATRIX_ITEMS:
        assert f"items+=('{item}')" in text, f"矩阵缺少 {item}"
    assert "PLATFORMS" not in text, "平台固定全量构建，不应再有 PLATFORMS 分支"
    assert "没有匹配的平台" not in text, "不应再有平台筛选的报错分支"
    for asset_name in (
        "mdcx-macos-${{ matrix.arch }}",
        "mdcx-windows-${{ matrix.arch }}",
        "mdcx-linux-${{ matrix.arch }}",
    ):
        assert f"name: {asset_name}" in text, f"产物名应与 release.yml 一致：{asset_name}"
    assert "pattern: mdcx-*" in text, "下载产物的 pattern 应与 release.yml 一致"


def test_python_314_pins_and_relock_fallback():
    """3.14 专属三处：解释器锁 3.14、构建前断言、uv sync 失败自动回退。"""
    text = _workflow()

    assert 'python-version: "3.14"' in text, "必须用 Python 3.14 构建"
    assert 'UV_PYTHON: "3.14"' in text, "需 UV_PYTHON 兜住 setup-python 之外的 uv 调用"
    assert "Verify Python 3.14 in use" in text, "缺少解释器断言，uv 可能悄悄挑到别的版本"
    assert "sys.version_info[:2] == (3, 14)" in text, "断言必须检查 sys.version_info"
    assert "uv sync --locked --all-extras --dev" in text, "仍需先用 --locked 严格校验"
    assert re.search(r"if ! uv sync --locked --all-extras --dev; then.*uv sync --all-extras --dev", text, re.S), (
        "uv sync --locked 失败必须自动回退重新解析（uv.lock 缺 cp314 wheel 时需要）"
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
        assert f"[ -s {asset} ]" in text, f"产物核对漏了 {asset}"
        assert f"file: {asset}" in text, f"缺少 {asset} 的上传步骤"

    gate = re.search(r"(?m)^\s{4}if: \$\{\{ (.+) \}\}$", text)
    assert gate is not None, "找不到 publish-release 的 if 条件"
    assert "!cancelled()" in gate.group(1), "用 !cancelled() 而非 always()，run 被取消时不再白跑发版"
    assert "needs.build-app.result == 'success'" in gate.group(1), (
        "发版条件必须核对 build-app 的真实结果（build-app 开了 continue-on-error，"
        "不能写 success()：needs 里任一失败腿都会让它整体跳过）"
    )
    assert re.search(r"(?m)^\s{4}continue-on-error: true$", text) is not None, (
        "continue-on-error 缺失时上面的 needs 结果门禁就没有意义"
    )


def test_release_uploads_are_idempotent():
    """重跑同一 commit 时不得因已存在同名 Release 而失败。"""
    text = _workflow()

    assert text.count("overwrite: true") >= _RELEASE_STEP_COUNT, (
        "Create Release 步骤需要 overwrite: true（同 release.yml），重跑时才不会失败"
    )
    assert "contents: write" in text, "创建 Release 需要 permissions: contents: write"
    assert text.count("- name: Create Release - ") == _RELEASE_STEP_COUNT, (
        f"应有 {_RELEASE_STEP_COUNT} 个 Create Release 步骤（macOS 两架构 + Windows + Linux）"
    )


def test_asset_names_match_release_workflow():
    """资产命名必须与 release.yml 一致，否则两个流程对同一 tag 的资产处理会分叉。"""
    text = _workflow()
    release = _RELEASE.read_text(encoding="utf-8")
    expected = (
        "asset_name: MDCx-${{ steps.metadata.outputs.tag }}-macos-aarch64-${{ github.sha }}.dmg",
        "asset_name: MDCx-${{ steps.metadata.outputs.tag }}-macos-x86_64-${{ github.sha }}.dmg",
        "asset_name: MDCx-${{ steps.metadata.outputs.tag }}-windows-x86_64-${{ github.sha }}.exe",
        "asset_name: MDCx-${{ steps.metadata.outputs.tag }}-linux-x86_64-${{ github.sha }}",
    )

    for asset_name in expected:
        assert asset_name in text, f"3.14 工作流缺少与 release.yml 一致的资产名：{asset_name}"
        assert asset_name in release, f"release.yml 不再使用该资产名，两个流程已分叉：{asset_name}"
    assert "release_name: ${{ steps.metadata.outputs.name }}" in text, "标题应沿用 metadata 的解析结果"
    assert 'echo "name=${version_name} (${tag})" >> "$GITHUB_OUTPUT"' in text, (
        "Release 标题应与 release.yml 相同（`VERSION_NAME (版本号)`）"
    )
