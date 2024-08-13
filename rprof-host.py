import psutil
import time
from datetime import datetime
from pathlib import Path
import argparse
import sys
 
#modified version of the script for monitoring the host metrics.
 
control_file = '.mon'
check_finish_freq = 10
 
option_function = {
    'disk': 'disk_io_counters()',
    'memory': 'virtual_memory()',
    'cpu': 'cpu_times()',
    'cpu_usage': 'cpu_percent(interval=None, percpu=True)',
    'network': 'net_io_counters()',
}
 
def config():
 
    parser = argparse.ArgumentParser(prog='rprof', description='resource usage profiler')
 
    parser.add_argument('-d', '--disk', action='store_true', help='Collect disk metrics')
    parser.add_argument('-m', '--memory', action='store_true', help='Collect memory metrics')
    parser.add_argument('-n', '--network', action='store_true', help='Collect network metrics')
    parser.add_argument('-c', '--cpu', action='store_true', help='Collect cpu metrics')
    parser.add_argument('-u', '--cpu_usage', action='store_true', help='Collect cpu usage per core')
    parser.add_argument('-o', '--output_dir', default='.', help='The output dir for the metrics file')
    parser.add_argument('-i', '--interval', type=float, default=1.5, help='Interval in seconds between each metric collection')
 
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
 
    return parser.parse_args()
 
def write_data(value_list: list, filename: str, mode: str):
 
    line = ''
    for value in value_list:
        line += f'{value};'
   
    line = line.strip(';')
    line += '\n'
 
    with open(filename, mode) as file:
        file.write(line)
 
def collect_data(args, create=False):
 
    timestamp = datetime.now()
 
    for option in option_function.keys():
        if eval(f'args.{option}'):
           
            if option == 'cpu_usage':
                data = eval(f'psutil.{option_function[option]}')
                if create:
                    write_data(['timestamp, usage'], f'{args.output_dir}/{option}.csv', 'w')
                else:
                    write_data([timestamp, data], f'{args.output_dir}/{option}.csv', 'a')
            else:
                data = eval(f'psutil.{option_function[option]}._asdict()')
 
                if create:
                    write_data(['timestamp'] + list(data.keys()), f'{args.output_dir}/{option}.csv', 'w')
                else:
                    write_data([timestamp] + list(data.values()), f'{args.output_dir}/{option}.csv', 'a')
 
def create_control_file(output_dir: Path):
 
    with open(output_dir / control_file, 'w') as file:
 
        file.write('0')
 
def check_finish(output_dir: Path):
 
    with open(output_dir / control_file, 'r') as file:
 
        a = int(file.read())
        return bool(int(a))
 
if __name__ == '__main__':
 
    args = config()
   
    counter = 0
    create_control_file(Path(args.output_dir))
 
    collect_data(args, create=True)
 
    while True:
 
        counter += 1
 
        collect_data(args)
 
        if counter == check_finish_freq:
 
            counter = 0
            if check_finish(Path(args.output_dir)):
                break
 
        time.sleep(args.interval)