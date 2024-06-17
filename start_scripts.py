import subprocess

scripts = [
    ("awsbench.py", "us-east-1","instance_info.json"),
    ("awsbench.py", "sa-east-1","instance_info.json"),
]

processes = []


for script, param1, param2 in scripts:
    process = subprocess.Popen(['python', script, param1, param2])
    processes.append(process)


for process in processes:
    process.wait()

print("All scripts have finished executing.")
