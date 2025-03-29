# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['C:\\Users\\Geralt\\PycharmProjects\\RivskiiDiary'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Добавляем все изображения в a.datas
a.datas += [
    ('img/add_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/add_icon.png', 'DATA'),
    ('img/copy_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/copy_icon.png', 'DATA'),
    ('img/delete_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/delete_icon.png', 'DATA'),
    ('img/down_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/down_icon.png', 'DATA'),
    ('img/edit_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/edit_icon.png', 'DATA'),
    ('img/folder_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/folder_icon.png', 'DATA'),
    ('img/icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/icon.png', 'DATA'),
    ('img/logo.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/logo.png', 'DATA'),
    ('img/template_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/template_icon.png', 'DATA'),
    ('img/up_icon.png', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/up_icon.png', 'DATA'),
    ('version.txt', 'C:/Users/Geralt/PycharmProjects/RivskiiDiary/version.txt', 'DATA'),
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Rivskii Diary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='C:/Users/Geralt/PycharmProjects/RivskiiDiary/img/program_icon.ico'
)
