"""Instrument: dump every frame width on NFO + watermark tabs (fresh window)."""
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))

from test_window_state_matrix import _goto, app, win  # noqa: F401,E402
from PyQt6 import QtWidgets  # noqa: E402


def _goto_tab(win, app, text):
    tw = win.Ui.tabWidget
    for i in range(tw.count()):
        if tw.tabText(i).strip() == text:
            tw.setCurrentIndex(i)
            app.processEvents()
            return
    raise AssertionError(f"no tab {text}")


def dump(win, tag):
    ui = win.Ui
    tw = ui.tabWidget
    inner = tw.findChild(QtWidgets.QWidget, "qt_tabwidget_stackedwidget")
    lines = [f"[{tag}]"]
    lines.append(f"win={win.width()} page_setting={ui.page_setting.width()}")
    lines.append(f"tabWidget={tw.width()} inner_stacked={inner.width() if inner else 'NONE'}")
    for name in ("tab_5", "tab_6", "tab_7"):
        w = getattr(ui, name, None)
        lines.append(f"{name}={w.width() if w else 'NONE'}")
    for sname in ("scrollArea_4", "scrollArea_13", "scrollArea_12"):
        sc = getattr(ui, sname, None)
        lines.append(f"{sname} vp={sc.viewport().width()}")
    for gname in ("groupBox_9", "groupBox_81"):
        gb = getattr(ui, gname, None)
        if gb is not None:
            lines.append(f"{gname} x={gb.x()} w={gb.width()}")
    return "\n".join(lines)


def test_instrument_frames(win, app):
    win.resize(1089, 900)
    win.show()
    for _ in range(3):
        win._sync_page_layouts()
        app.processEvents()
    _goto(win, app, "page_setting")
    _goto_tab(win, app, "NFO")
    for _ in range(3):
        win._sync_page_layouts()
        app.processEvents()
    out = [dump(win, "NFO-visible")]
    _goto_tab(win, app, "水印")
    for _ in range(3):
        win._sync_page_layouts()
        app.processEvents()
    out.append(dump(win, "WM-visible"))
    with open(r"D:\@Data\MDCx\frames.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
