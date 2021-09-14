import sys; sys.path.extend(['../../'])
import subprocess

def run_sync_shell(cmd):
    print(cmd)
    exp_subprocess = subprocess.Popen(cmd, stderr=subprocess.PIPE, shell=True)

    while True:
        out = exp_subprocess.stderr.read(1)
        if out == '' and exp_subprocess.poll() != None:
            break
        if out != '':
            sys.stdout.write(out)
            sys.stdout.flush()

    #exp_subprocess.wait()

