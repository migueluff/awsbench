instance_core = 24
threads_list = ''
for idx in range(0, instance_core):
    if idx == 0:
        threads_list = str(idx)
    else:
        threads_list += ' ' + str(idx)

cmd = f'export GOMP_CPU_AFFINITY="{threads_list}"'
print(cmd)