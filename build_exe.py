# build_exe.py
import PyInstaller.__main__
import os

# Создаем .exe файл
PyInstaller.__main__.run([
    'epb_runner.py',
    '--onefile',
    '--console',
    '--name=EnergyScraperManager',
    '--clean',
    '--add-data=aggregate.py;.',
    '--add-data=run_upload.bat;.' if os.path.exists('run_upload.bat') else '',
    '--hidden-import=psutil',
    '--hidden-import=argparse',
    '--hidden-import=glob',
    '--hidden-import=json',
    '--hidden-import=time',
    '--hidden-import=os',
    '--hidden-import=subprocess',
    '--hidden-import=threading',
    '--hidden-import=datetime',
    '--hidden-import=pathlib'
])