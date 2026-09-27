"""Probe: sibling right-margin constancy (tab frame) across widths. UTF-8 out."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, "tests")

from test_window_state_matrix import _ensure_app, _goto  # noqa: E402
from PyQt6.QtCore import QPoint  # noqa: E402

app = _ensure_app()

from unittest import mock  # noqa: E402

from mdcx.controllers.main_window import main_window as mw_mod  # noqa: E402
from mdcx.controllers.main_window import style as style_mod  # noqa: E402
from mdcx.consts import MAIN_PATH  # noqa: E402

with mock.patch.object(mw_mod, "run_startup_health_checks", lambda: None), mock.patch.object(
    mw_mod, "show_netstatus", lambda: None
), mock.patch.object(mw_mod, "check_version", lambda: None), mock.patch.object(
    mw_mod, "save_remain_list", lambda: None
), mock.patch.object(
    mw_mod.MyMAinWindow, "set_style", lambda self: None
), mock.patch.object(
    mw_mod, "apply_site_priority_theme", lambda _window: None
), mock.patch.object(
    style_mod.resources, "qtr", lambda p: str(MAIN_PATH / "resources" / p)
):
    win = mw_mod.MyMAinWindow()
    for t in ("timer", "timer_scrape", "timer_update", "timer_remain_task"):
        getattr(win, t).stop()
    ui = win.Ui

    def tab_of(box):
        w = box
        while w.parent() is not None and w.parent() is not ui.tabWidget:
            w = w.parent()
        return w

    def goto_tab_by_box(box, name):
        _goto(win, app, "page_setting")
        for i in range(ui.tabWidget.count()):
            if ui.tabWidget.widget(i).findChild(type(box), name) is not None:
                ui.tabWidget.setCurrentIndex(i)
                break
        app.processEvents()

    out = []
    for w in (700, 900, 1089, 1500, 1900):
        win.resize(w, 900)
        # NFO side
        goto_tab_by_box(ui.groupBox_81, "groupBox_81")
        for _ in range(3):
            win._sync_page_layouts()
            app.processEvents()
        tab_nfo = tab_of(ui.groupBox_81)
        r81 = ui.groupBox_81.mapTo(tab_nfo, QPoint(ui.groupBox_81.width(), 0)).x()
        # watermark side
        goto_tab_by_box(ui.groupBox_31, "groupBox_31")
        for _ in range(3):
            win._sync_page_layouts()
            app.processEvents()
        tab_wm = tab_of(ui.groupBox_31)
        r31 = ui.groupBox_31.mapTo(tab_wm, QPoint(ui.groupBox_31.width(), 0)).x()
        out.append(
            f"W={w} tabnfo={tab_nfo.width()}({tab_nfo.objectName()}) "
            f"gb81x={ui.groupBox_81.x()}w={ui.groupBox_81.width()} Rtab={r81} "
            f"M_nfo={tab_nfo.width() - r81} | tabwm={tab_wm.width()}({tab_wm.objectName()}) "
            f"gb31x={ui.groupBox_31.x()}w={ui.groupBox_31.width()} Rtab={r31} "
            f"M_wm={tab_wm.width() - r31}"
        )
    with open(r"C:\Users\ZhouHan\AppData\Local\Temp\opencode\probe_gb2.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("PROBE_DONE", flush=True)
