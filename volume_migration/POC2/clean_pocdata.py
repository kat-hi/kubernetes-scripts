import subprocess

subprocess.run('kubectl delete deployment poc1-test -n testing', shell=True)
subprocess.run('kubectl delete pod csi-migration-toolpod -n testing', shell=True)
subprocess.run('kubectl delete pvc poctestpvc -n testing', shell=True)
subprocess.run('kubectl delete pvc poctestpvc2 -n testing', shell=True)



