# Maintained PyInstaller specification for the framework-equivalent distributable.
from pathlib import Path

project = Path(SPECPATH)
a = Analysis([str(project / 'app.py')], pathex=[str(project)], binaries=[], datas=[], hiddenimports=[],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StudentInformationSystem', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name='StudentInformationSystem')
