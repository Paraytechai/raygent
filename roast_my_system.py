import os
import platform
import sys
import ctypes
import shutil
import random

def get_free_space_gb():
    try:
        total, used, free = shutil.disk_usage("C:\\")
        return free // (1024**3)
    except Exception:
        return 0

def get_total_ram_gb():
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return int(stat.ullTotalPhys // (1024**3))
    except Exception:
        return 0

def main():
    print("=" * 60)
    print(" RAYGENT SYSTEM DIAGNOSTIC & ROAST TERMINAL v1.0 ")
    print("=" * 60)
    
    # Gather specs
    os_name = platform.system()
    os_release = platform.release()
    cpu_info = platform.processor() or "Unknown CPU"
    python_ver = sys.version.split()[0]
    username = os.environ.get("USERNAME", "Unknown User")
    ram_gb = get_total_ram_gb()
    free_gb = get_free_space_gb()
    
    # Display specs
    print(f"[*] Checking specs for user: '{username}'")
    print(f"[*] OS: {os_name} {os_release}")
    print(f"[*] Processor: {cpu_info}")
    print(f"[*] Installed RAM: {ram_gb} GB")
    print(f"[*] C:\\ Free Space: {free_gb} GB")
    print(f"[*] Python Engine: {python_ver}")
    print("-" * 60)
    
    # Now, let the roasting begin!
    print("RAYGENT SAYS:\n")
    
    # User handle roast
    if username.lower() == "cyber":
        print("💻 'cyber'? What is this, a 1995 hacker movie starring Angelina Jolie? Are we hacking the Gibson, or are you just hiding from math homework behind a cool alias? Ray, dial down the Matrix, we're on Windows here.")
    else:
        print(f"👤 Ray, logging in under '{username}'? Real creative. Your system admin must have been asleep at the wheel.")
        
    # RAM roast
    if ram_gb > 0:
        if ram_gb < 16:
            print(f"🎰 {ram_gb} GB of RAM? Buddy, my whiskey glass has more capacity than this machine. Are we running Chrome tabs or just calculating single-digit math problems on a smart calculator?")
        else:
            print(f"🎰 {ram_gb} GB of RAM... okay, you've got some heavy horsepower. Too bad it's mostly being hogged by 45 unclosed StackOverflow tabs and a background music player while you stare blankly at basic SQL queries.")
            
    # Storage roast
    if free_gb > 0:
        if free_gb < 20:
            print(f"📂 {free_gb} GB left on C:\\? You're playing digital chicken with your operating system, Ray. One Windows update or one high-res picture of a bourbon bottle and this whole house of cards collapses!")
        else:
            print(f"📂 {free_gb} GB of free space. Nice, plenty of room to store all those unfinished projects you started at 2 AM after three drinks and forgot about by sunrise.")

    # MATH-121 and SIS-230 Easter eggs
    print("\n📚 COURSE COMPATIBILITY CHECK:")
    print("🔺 MATH-121: Zoe Likoudis right-triangle calculations... [COMPATIBLE]")
    print("   -> Sarcasm engine detects enough CPU power to solve 'a² + b² = c²' without bursting into flames, barely.")
    print("💾 SIS-230: Relational Database SQL schemas... [COMPATIBLE]")
    print("   -> Running a local db here is technically possible, but your storage suggests a structure looser than a spaghetti junction junction-table.")
    
    print("\n" + "=" * 60)
    print(" ROAST COMPLETE. NOW GET BACK TO WORK, RAY! ")
    print("=" * 60)

if __name__ == "__main__":
    main()
