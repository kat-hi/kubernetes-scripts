import subprocess
import time
from shutil import copyfile

from kubernetes import client, config
from kubernetes.client.models.v1_persistent_volume_claim import V1PersistentVolumeClaim
import os
import sys
import yaml
from kubernetes.client.exceptions import ApiException
import urllib3
import json
import colorama
from colorama import Fore
import dialog

###############################
# commandline arguments:
# python3 csi-migration.py -a (include all namespaces)
# python3 csi-migration.py -n namespace1 namespace2 (include two namespaces: 'namespace1' and 'namespace2'
# python3 csi-migration.py (without argument: use testnamespace)
###############################

#  get deployments with flexvolumes
#  set replicaset = 0
#  get pvc that is referenced in deployment -- DONE
#  create new pvc with same data but new storage-class -- DONE
#  start tool pod that mounts both - old and new pvc -- DONE
#  execute rsync to copy data from old to new -- DONE
#  kill tool-pod -- DONE
#  add new pvc and volume to the deployment -- DONE
#  remove old pvc from deployment -- DONE
#  apply new deployment -- DONE


def kubectl(command, namespace):
    data = subprocess.check_output(f'kubectl {command} -n {namespace}', shell=True)
    try:
        return json.loads(data)
    except Exception:
        data = data.decode('utf-8')
        print(f'{Fore.WHITE} {data}')
        return data


def _reset_toolpod_yaml():
    with open(f'csi-migration-tool-pod.yaml', 'r') as file:
        pod = yaml.load(file, Loader=yaml.FullLoader)
        del pod['spec']['containers'][0]['volumeMounts']
        del pod['spec']['volumes']
    with open(f'csi-migration-tool-pod.yaml', 'w') as file:
        yaml.dump(pod, file, allow_unicode=True)


def start_toolpod(namespace):
    subprocess.run(f'kubectl apply -f csi-migration-tool-pod.yaml -n {namespace}', shell=True)
    print(f"{Fore.GREEN} applying toolpod...")
    found = False
    while not found:
        time.sleep(3.0)
        try:
            res = subprocess.check_output(f'kubectl get pod csi-migration-toolpod -n {namespace}', shell=True)
            if res:
                print(str(res.decode('utf-8')))
                found = True
        except subprocess.CalledProcessError:
            pass
    print(f"{Fore.GREEN} toolpod is running.")
    time.sleep(2.0)


def prepare_toolpod(namespace, saved_old_volumes, mountpaths):
    print(f"{Fore.GREEN} preparing toolpod...")
    print(f"{Fore.GREEN} volumes to be migrated: {len(saved_old_volumes)}")
    volume_mount_old = []
    volume_mount_new = []

    old_volumes = []
    new_volumes = []

    print(os.getcwd())

    with open(f'csi-migration-tool-pod-template.yaml', 'r') as file:
        pod = yaml.load(file, Loader=yaml.FullLoader)
        pod['metadata']['namespace'] = namespace
        old_new_pathmapper = {}

        for j in range(0, len(saved_old_volumes)):
            old_volume_name = saved_old_volumes[j]
            new_volume_name = old_volume_name+'-csi'

            for i in range(0, len(mountpaths)):
                if mountpaths[i]['name'] == old_volume_name:
                    mountpath = mountpaths[i]['mountPath']

            volume_mount_old.append({'mountPath': f'/mnt/old/{j}', 'name': old_volume_name})
            volume_mount_new.append({'mountPath': f'{mountpath}', 'name': new_volume_name})

            old_new_pathmapper[f'/mnt/old/{j}'] = mountpath

            old_volumes.append({'name': old_volume_name, 'persistentVolumeClaim': {'claimName': old_volume_name}})
            new_volumes.append({'name': new_volume_name, 'persistentVolumeClaim': {'claimName': new_volume_name}})

        pod['spec']['containers'][0]['volumeMounts'] = volume_mount_new + volume_mount_old
        pod['spec']['volumes'] = old_volumes + new_volumes

    with open(f'csi-migration-tool-pod.yaml', 'w') as file:
        yaml.dump(pod, file, allow_unicode=True)

    return old_new_pathmapper


def _remove_old_volume_from_deployment(old_mounts, volume_list, old_vol):
    print(f"{Fore.GREEN} remove old volume(s) from deployment definition:")
    for i in range(len(old_mounts)-1):
        if old_mounts[i]['name'] == old_vol:
            print(f"{Fore.GREEN} {old_mounts[i]['name']} deleted.")
            del old_mounts[i]
        if volume_list[i]['name'] == old_vol:
            print(f"{Fore.GREEN} {volume_list[i]['name']} deleted.")
            del volume_list[i]
    return old_mounts, volume_list


def get_volume_list_and_mount_paths(k8s_deployment):
    last_applied = None
    try:
        last_applied = k8s_deployment.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration']
        last_applied = (eval(last_applied))
    except ApiException as e:
        print(e.body)
    if last_applied:
        mount_paths = last_applied['spec']['template']['spec']['containers'][0]['volumeMounts']
        volume_list = last_applied['spec']['template']['spec']['volumes']
        return mount_paths, volume_list


def replace_old_volumes_with_new(k8s_deployment, saved_old_volumes):
    last_applied = None
    try:
        last_applied = k8s_deployment.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration']
        last_applied = (eval(last_applied))
    except ApiException as e:
        print(e.body)
    if last_applied:
        current_volume_mounts = last_applied['spec']['template']['spec']['containers'][0]['volumeMounts']
        old_mount_paths = last_applied['spec']['template']['spec']['containers'][0]['volumeMounts']
        volume_list = last_applied['spec']['template']['spec']['volumes']
        for current_mount in current_volume_mounts:
            for old_vol in saved_old_volumes:
                if current_mount['name'] == old_vol:
                    mountpath = current_mount['mountPath']
                    volume_mount = {'mountPath': mountpath, 'name': old_vol + '-csi'}
                    print(f"{Fore.GREEN} add new volume mount to deployment {volume_mount} ")
                    old_mount_paths.append(volume_mount)
                    volume_list.append({'name': old_vol + '-csi', 'persistentVolumeClaim': {'claimName': old_vol + '-csi'}})


        for old_vol in saved_old_volumes:
            _remove_old_volume_from_deployment(old_mount_paths, volume_list, old_vol)

        last_applied['spec']['template']['spec']['volumes'] = volume_list
        last_applied['spec']['template']['spec']['containers'][0]['volumeMounts'] = old_mount_paths

        return last_applied


def create_new_deployment(last_applied):

    try:
        with open('deployment.json', 'w') as file:
            json.dump(last_applied, file)
        print(f"{Fore.GREEN} try create deployment '{last_applied['metadata']['name']}' i"
              f"n namespace '{last_applied['metadata']['namespace']}'")
        subprocess.run('kubectl apply -f deployment.json', shell=True)
        print(f"{Fore.GREEN} deployment created successfully")
    except ApiException as e:
        print(f'{Fore.RED} creating deployment failed: {e.body}')


def create_csi_volumes(volumes, namespace):
    saved_old_volumes = []
    for vol in volumes:
        k8s_vol = core_v1.read_namespaced_persistent_volume_claim(namespace=namespace, name=vol.name)
        k8s_vol.spec.storage_class_name = 'cephcsi'

        last_applied = k8s_vol.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration']
        last_applied = (eval(last_applied))
        last_applied['spec']['storageClassName'] = 'cephcsi'

        labels = last_applied['metadata']['labels'].items()
        new_labels = {}
        for key, value in labels:
            new_labels[key] = value + '-csi'
        last_applied['metadata']['labels'] = new_labels

        name = last_applied['metadata']['name']
        last_applied['metadata']['name'] = name + '-csi'
        pvc = V1PersistentVolumeClaim(
            spec=last_applied['spec'], metadata=last_applied['metadata'], kind=last_applied['kind'], api_version=last_applied['apiVersion'])
        saved_old_volumes.append(name)

        try:
            core_v1.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
            print(f"{Fore.GREEN} PVC created.")
        except ApiException as e:
            print(f"{Fore.RED} PVC {name} wasn't created.")
            pass
    return saved_old_volumes


def get_namespaces_scope(mode):
    ns = ['testing']
    if mode == '-a':
        ns = [namespace.metadata.name for namespace in core_v1.list_namespace().items]
    elif mode == '-n':
        ns = [namespace for namespace in sys.argv if namespace != __file__ if namespace != '-n']
    return ns


def insert_mountpath_into_rsync_template(mountpaths, old_new_pathmapper):
    copyfile('rsync_template.py', 'rsync.py')

    mountpathnames = [mountpath['mountPath'] for mountpath in mountpaths]

    with open('rsync.py', 'a+') as outfile:
        for i in range(0, len(mountpaths)):
            outfile.write(f'test{i}')

    with open('rsync_template.py', 'r') as f:
        with open('rsync.py', 'w') as f2:
            for i in range(0, len(mountpathnames)):
                f2.write(f'old_new_pathmapper = {str(old_new_pathmapper)}\n')
                f2.write(f'mountpaths = {str(mountpaths)}\n')
            f2.write(f.read())


def build_and_push_rsync_image():
    image_version = 'v14'
    subprocess.run(f'docker build -t lockat/toolpod:{image_version} .', shell=True)
    subprocess.run(f'docker push lockat/toolpod:{image_version}', shell=True)


if __name__ == '__main__':
    # defaults
    mode = ''
    testing = True

    dialog.want_to_proceed()

    config.load_kube_config('~/.kube/config')
    urllib3.disable_warnings()
    colorama.init(autoreset=True)
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    namespaces = get_namespaces_scope(mode)

    for namespace in namespaces:
        deployments = kubectl("get Deployments -o jsonpath='{.items}'", namespace)

        for d in deployments:
            deployment_name = ''
            is_flexvolume = False
            volume = d['spec']['template']['spec']['volumes']

            if testing:
                # for security reasons while testing: only choose deployments that explicitly contain 'test' in their name
                # and ignore that we only want to find flexvolumes
                if 'test' in d['metadata']['name']:
                    deployment_name = d['metadata']['name']
            else:
                deployment_name = d['metadata']['name']
                try:
                    is_flexvolume = volume[0]['flexVolume']
                except KeyError:
                    is_flexvolume = None

            if is_flexvolume or testing:
                kubectl(f'scale deploy {deployment_name} --replicas=0', namespace)
                k8s_deployment = apps_v1.read_namespaced_deployment(namespace=namespace, name=deployment_name)
                current_volumes = k8s_deployment.spec.template.spec.volumes
                saved_old_volumes = create_csi_volumes(current_volumes, namespace)
                mountpaths = get_volume_list_and_mount_paths(k8s_deployment)[0]
                old_new_pathmapper = prepare_toolpod(namespace, saved_old_volumes, mountpaths) # mount old and new volume(s)
                insert_mountpath_into_rsync_template(mountpaths, old_new_pathmapper)
                build_and_push_rsync_image()
                start_toolpod(namespace)  # execute rsync
                last_applied = replace_old_volumes_with_new(k8s_deployment, saved_old_volumes)  # add mountPath and pvc
                create_new_deployment(last_applied)  # apply to k8s
