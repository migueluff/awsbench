import subprocess
import time
import sys
import signal



def load_commands(file_path):
    with open(file_path, 'r') as file:
        commands = [line.strip() for line in file if line.strip()]
    return commands


def run_commands(commands):
    for command in commands:
        print(f"Running command: {command}")
        result = subprocess.run(command, shell=True)
        if result.returncode != 0:
            print(f"Command {command} failed with return code {result.returncode}", file=sys.stderr)
        else:
            print(f"Command {command} executed successfully")


def signal_handler(sig, frame):
    print('You pressed Ctrl+C! Exiting gracefully...')
    sys.exit(0)

def main(commands_file, interval_hours):
    commands = load_commands(commands_file)
    interval_seconds = interval_hours * 3600

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        print(f"Running commands at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        run_commands(commands)
        print(f"Waiting for {interval_hours} hours...")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python start_scripts.py <commands_file> <interval_hours>")
        sys.exit(1)

    commands_file = sys.argv[1]
    interval_hours = float(sys.argv[2])

    main(commands_file, interval_hours)
