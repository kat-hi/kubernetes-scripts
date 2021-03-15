import json
import subprocess
import pandas as pd
from kubernetes import client, config

import urllib3

def kubectl(command, namespace):
    data = subprocess.check_output(f'kubectl {command} -n {namespace}', shell=True)
    return json.loads(data)


if __name__ == '__main__':
    config.load_kube_config('~/.kube/config')
    urllib3.disable_warnings()
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    pvs = core_v1.list_persistent_volume().items
    print(len(pvs))
    count_labels = 0
    for pv in pvs:
        try:
            flex = pv.spec.flex_volume
            try:
                labels = pv.metadata.annotations
                print(labels)
                if labels:
                    count_labels += 1
                    print(labels)
            except Exception:
                pass
        except Exception:
            pass
