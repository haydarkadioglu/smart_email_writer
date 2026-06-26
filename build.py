import os
import sys
import subprocess
from pathlib import Path

def run():
    print("=========================================")
    print("   SEW AI - Building EXE     ")
    print("=========================================\n")
    
    # 1. Install PyInstaller if not present
    try:
        import PyInstaller
        print("[OK] PyInstaller is already installed.")
    except ImportError:
        print("[INFO] PyInstaller not found. Installing via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller installed successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to install PyInstaller: {e}")
            sys.exit(1)
            
    # 2. Define template directory path
    # On Windows, PyInstaller expects format: "source_path;dest_path"
    templates_src = Path("ui_webview") / "templates"
    templates_dest = Path("ui_webview") / "templates"
    
    add_data_flag = f"{templates_src}{os.pathsep}{templates_dest}"
    
    # 3. Assemble pyinstaller command
    # --onefile: package into a single executable
    # --noconsole: hide the command window when running the app
    # --add-data: bundle the html/css/js templates
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--icon=app_icon.ico",
        f"--add-data={add_data_flag}",
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--hidden-import=pdfplumber",
        "--hidden-import=pdfminer",
        "--hidden-import=pdfminer.high_level",
        "--hidden-import=pdfminer.layout",
        "--hidden-import=pdfminer.pdfinterp",
        "--hidden-import=pdfminer.pdfpage",
        "--hidden-import=pdfminer.pdfdocument",
        "--hidden-import=pdfminer.pdfparser",
        "--hidden-import=pdfminer.pdftypes",
        "--hidden-import=pdfminer.psparser",
        "--hidden-import=pdfminer.utils",
        "--hidden-import=pdfminer.converter",
        "--hidden-import=pdfminer.cmapdb",
        "--hidden-import=pdfminer.encodingdb",
        "--hidden-import=pdfminer.fontmetrics",
        "--hidden-import=pdfminer.image",
        "--hidden-import=pdfminer.pdfcolor",
        "--hidden-import=pdfminer.pdfdevice",
        "--hidden-import=pdfminer.pdfobj",
        "--hidden-import=pdfminer.runlength",
        "--hidden-import=pdfminer.ccitt",
        "--hidden-import=pdfminer.arcfour",
        "--hidden-import=pdfminer.lzw",
        "--hidden-import=pdfminer.ascii85",
        "--hidden-import=docx",
        "--hidden-import=docx.opc",
        "--hidden-import=docx.opc.constants",
        "--hidden-import=docx.opc.part",
        "--hidden-import=docx.opc.package",
        "--hidden-import=docx.opc.pkgreader",
        "--hidden-import=docx.opc.rel",
        "--hidden-import=lxml",
        "--hidden-import=lxml.etree",
        "--hidden-import=lxml._elementpath",
        "--hidden-import=charset_normalizer",
        "--collect-submodules=pdfplumber",
        "--collect-submodules=pdfminer",
        "--collect-submodules=docx",
        "--name=SmartEmailWriter",
        "main.py"
    ]
    
    print(f"\nBuilding executable...")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        subprocess.check_call(cmd)
        print("\n=========================================")
        print(" BUILD COMPLETED SUCCESSFULLY! ")
        print("=========================================")
        print(f"Your executable is ready: {Path('dist/SmartEmailWriter.exe').absolute()}")
        print("Note: You can copy and run this EXE anywhere. Make sure to place your .env file")
        print("in the same directory if you want it to load your API keys automatically.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed with exit code: {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    run()
