from cx_Freeze import setup, Executable

setup(
    name="BILL_GENERATION",
    version="1.0",
    description="BILL_GENERATION",
    executables=[Executable("main.py")],
    options={
        "build_exe": {
            "base": "Win32GUI"  # Hide the console window
        }
    }
)
