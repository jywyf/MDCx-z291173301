"""Probe groupBox_81 stretch trajectory: registry values + per-round vp/width/sb."""
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
import conftest  # noqa: F401  (fixture recipe lives in test module; probe inlines it)

app = QApplication.instance() or QApplication([])
out = []
try:
    from mdcx.controllers.main_window.main_window import MyMAinWindow
    from mdcx.views.CustomClass import CustomScrollArea
    win = MyMAinWindow()
    try:
        win.set_style(None)
    except Exception:
        pass
    try:
        win.stop_all_timers()
    except Exception:
        pass
    ui = win.Ui
    gb81 = ui.groupBox_81
    # goto page_setting + NFO tab by box (same recipe as group test)
    for i in range(ui.stackedWidget.count()):
        if ui.stackedWidget.widget(i).objectName() == "page_setting":
            ui.stackedWidget.setCurrentIndex(i)
            break
    app.processEvents()
    for i in range(ui.tabWidget.count()):
        if ui.tabWidget.widget(i).findChild(type(gb81), "groupBox_81") is not None:
            ui.tabWidget.setCurrentIndex(i)
            break
    app.processEvents()
    win.show()
    win.resize(1089, 900)
    for _ in range(3):
        app.processEvents()
    sc13 = ui.scrollArea_13
    content = sc13.widget()
    reg = getattr(content, "_wide_children_design", None)
    for e in (reg or []):
        if e.widget is gb81:
            out.append(f"REG entry gb81={e.geometry} design_w={getattr(content, '_wide_children_design_width', None)}")
    sb = sc13.verticalScrollBar()
    out.append(f"BASE vp={sc13.viewport().width()} gb81w={gb81.width()} sbvis={sb.isVisible()} sbw={sb.width()}")
    gb81.resize(gb81.width() - 64, gb81.height())
    app.processEvents()
    for r in range(6):
        win._sync_page_layouts()
        vp0 = sc13.viewport().width()
        w0 = gb81.width()
        app.processEvents()
        out.append(f"R{r} sync_vp={vp0} set_w={w0} | settled_vp={sc13.viewport().width()} settled_w={gb81.width()} sbvis={sb.isVisible()}")
except Exception as e:
    import traceback
    out.append("PROBE-ERROR " + repr(e))
    out.append(traceback.format_exc())
with open(r"C:\Users\ZhouHan\AppData\Local\Temp\opencode\probe_gb.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("PROBE-DONE")
