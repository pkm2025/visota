import subprocess
p = subprocess.Popen(
    [r"C:\mmm\visota\.venv\Scripts\python.exe", "manage.py", "runserver", "0.0.0.0:8903", "--noreload"],
    cwd=r"C:\mmm\visota",
    creationflags=0x00000008 | 0x00000200,
    stdout=open(r"C:\mmm\visota\server.log","w"),
    stderr=subprocess.STDOUT,
)
print("launched", p.pid)
