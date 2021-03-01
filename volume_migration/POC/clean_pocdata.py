import subprocess

subprocess.run('kubectl delete deployment test-mongo1 -n testing', shell=True)
subprocess.run('kubectl delete pod csi-migration-toolpod-test-mongo1 -n testing', shell=True)
subprocess.run('kubectl delete pvc mongo-pvc-test -n testing', shell=True)
subprocess.run('kubectl delete pvc mongo-pvc-test-csi -n testing', shell=True)



