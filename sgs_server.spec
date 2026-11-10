# PyInstaller: python -m PyInstaller sgs_server.spec  ->  dist/sgs-server/
import os
datas = [
    ("web", "web"),
    ("strategies", "strategies"),   # 武將專屬策略檔 (strategy_agent.py 用檔案路徑動態載入)
    ("character_images.json", "."),
    ("characters.md", "."),
    ("CHANGELOG.md", "."),
]
datas = [(s, d) for s, d in datas if os.path.exists(s)]
# 開發機上的縮圖快取不要打包
a = Analysis(
    ["server.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=["PIL.Image"],
    excludes=["tkinter", "numpy", "matplotlib"],
)
a.datas = [d for d in a.datas if not d[0].replace("\\", "/").startswith("web/cache/")]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="sgs-server", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="sgs-server")
