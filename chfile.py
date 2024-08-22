from os import listdir
from os.path import isfile, join

onlyfiles = [f for f in listdir('.') if isfile(join('.', f))]
filt = [x for x in onlyfiles if 'disk' in x and ('2_alg:' in x or '1_alg:' in x or '0_alg:ft' in x or '0_alg:mg' in x)]
for filename in filt:
	with open(filename, 'r') as file:
		lines = file.readlines()
		lines.insert(0, 'timestamp;read_count;write_count;read_bytes;write_bytes;read_time;write_time;read_merged_count;write_merged_count;busy_time\n')
	with open(filename, 'w') as file:
		file.write(''.join(lines))
