import copy
import os
import sys
from shutil import rmtree
from kubernetes.client.models.v1_persistent_volume_claim import V1PersistentVolumeClaim
from kubernetes.client.exceptions import ApiException
from kubernetes import client, config
from colorama import Fore
import argparse
import colorama
import dialog
import json
import subprocess
import time
import urllib3
import yaml

image_version = 'v20'


def kubectl(command, namespace):
    data = subprocess.check_output(f'kubectl {command} -n {namespace}', shell=True)
    try:
        return json.loads(data)
    except Exception:
        data = data.decode('utf-8')
        print(f'{Fore.WHITE} {data}')
        return data


def start_toolpod(namespace, deployname):
    dirpath = _get_resourcedir(namespace, deployname)
    subprocess.run(f"kubectl apply -f {dirpath}/csi-migration-tool-pod.json -n {namespace}", shell=True)
    wait_for_creating_or_terminating(name=f'csi-migration-toolpod-{deployname}', has_pods=False, resource='pods')


def prepare_toolpod(namespace, saved_old_volumeclaims, deploy_name):
    mountpaths = _get_volume_list_and_mount_paths(last_applied_deployment)[0]

    print(f"{Fore.GREEN} preparing toolpod...")
    print(f"{Fore.WHITE} volumes to be migrated: {len(saved_old_volumeclaims)}")
    vol_dict = {'old_mounts': [], 'new_mounts': [], 'old_claims': [], 'new_claims': []}

    with open(f'csi-migration-tool-pod-template.yaml', 'r') as file:
        pod = yaml.load(file, Loader=yaml.FullLoader)
        pod['metadata']['name'] = f'csi-migration-toolpod-{deploy_name}'
        pod['metadata']['namespace'] = namespace

        pathmapper = {}

        for j in range(0, len(saved_old_volumeclaims)):
            old_claimname = saved_old_volumeclaims[j]
            new_claimname = old_claimname + '-csi'

            for i in range(0, len(mountpaths)):
                if mountpaths[i]['name'] == old_claimname:
                    mountpath = mountpaths[i]['mountPath']

            vol_dict['old_mounts'].append({'mountPath': f'/mnt/old/{j}', 'name': old_claimname})
            vol_dict['new_mounts'].append({'mountPath': f'{mountpath}', 'name': new_claimname})

            pathmapper[f'/mnt/old/{j}'] = mountpath

            vol_dict['old_claims'].append(
                {'name': old_claimname, 'persistentVolumeClaim': {'claimName': old_claimname}})
            vol_dict['new_claims'].append(
                {'name': new_claimname, 'persistentVolumeClaim': {'claimName': new_claimname}})

        pod['spec']['containers'][0]['volumeMounts'] = vol_dict['new_mounts'] + vol_dict['old_mounts']
        pod['spec']['volumes'] = vol_dict['old_claims'] + vol_dict['new_claims']

        toolpod_env_vars = [{'name': 'pathmapper', 'value': json.dumps(pathmapper)},
                            {'name': 'mountpaths', 'value': json.dumps(mountpaths)}]

        pod['spec']['containers'][0]['env'] = toolpod_env_vars

    persist_resource(last_applied=pod, filename=f'{_get_resourcedir(namespace, deploy_name)}/csi-migration-tool-pod')


def _remove_old_volume_from_deployment(old_mounts, volume_list, old_vol):
    print(f"{Fore.WHITE} remove old volume(s) from deployment definition:")
    for i in range(len(old_mounts) - 1):
        if old_mounts[i]['name'] == old_vol:
            print(f"{Fore.RED} mount {old_mounts[i]['name']} deleted.")
            del old_mounts[i]
        if volume_list[i]['name'] == old_vol:
            print(f"{Fore.RED} volume {volume_list[i]['name']} deleted.")
            del volume_list[i]
    return old_mounts, volume_list


def get_last_applied_deployment(k8s_deployment):
    try:
        last_applied = k8s_deployment.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration']
        last_applied = (eval(last_applied))
        return last_applied
    except ApiException as e:
        return None


def _get_volume_list_and_mount_paths(last_applied):
    mount_paths = last_applied['spec']['template']['spec']['containers'][0]['volumeMounts']
    volume_list = last_applied['spec']['template']['spec']['volumes']
    return mount_paths, volume_list


def replace_old_volumes_with_new(last_applied, saved_old_volume_claims):
    modified_last_applied_deployment = copy.deepcopy(last_applied)
    current_volume_mounts = modified_last_applied_deployment['spec']['template']['spec']['containers'][0][
        'volumeMounts']
    old_mount_paths = modified_last_applied_deployment['spec']['template']['spec']['containers'][0]['volumeMounts']
    volume_list = modified_last_applied_deployment['spec']['template']['spec']['volumes']
    for current_mount in current_volume_mounts:
        for old_claim in saved_old_volume_claims:
            if current_mount['name'] == old_claim:
                mountpath = current_mount['mountPath']
                volume_mount = {'mountPath': mountpath, 'name': old_claim + '-csi'}
                print(f"{Fore.WHITE} add new volume mount to deployment {volume_mount}")
                old_mount_paths.append(volume_mount)
                volume_list.append({'name': old_claim + '-csi',
                                    'persistentVolumeClaim': {'claimName': old_claim + '-csi'}})

    for old_claim in saved_old_volume_claims:
        _remove_old_volume_from_deployment(old_mount_paths, volume_list, old_claim)

    modified_last_applied_deployment['spec']['template']['spec']['volumes'] = volume_list
    modified_last_applied_deployment['spec']['template']['spec']['containers'][0]['volumeMounts'] = old_mount_paths

    return modified_last_applied_deployment


def create_new_deployment(deployname, ns, filename):
    try:
        print(f"{Fore.WHITE} create deployment '{deployname}' i"
              f"n namespace '{ns}'")
        subprocess.run(f'kubectl apply -f {filename}.json', shell=True)
        print(f"{Fore.GREEN} deployment created successfully")
    except ApiException as e:
        print(f'{Fore.RED} creating deployment failed: {e.body}')


def create_csi_volumes(volume_claims, ns, new_storageclass):
    saved_old_volumeclaims = []
    for volClaim in volume_claims:
        volClaim.spec.storage_class_name = new_storageclass

        last_applied_volumeclaim = volClaim.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration']
        persist_resource(last_applied_volumeclaim, f'{_get_resourcedir(namespace, deploy_name)}/old_pvc')
        last_applied_volumeclaim = (eval(last_applied_volumeclaim))
        last_applied_volumeclaim['spec']['storageClassName'] = new_storageclass
        del last_applied_volumeclaim['spec']['volumeName']

        if 'labels' in last_applied_volumeclaim['metadata'].keys():
            labels = last_applied_volumeclaim['metadata']['labels'].items()
            new_labels = {}
            for key, value in labels:
                new_labels[key] = value + '-csi'
            last_applied_volumeclaim['metadata']['labels'] = new_labels

        name = last_applied_volumeclaim['metadata']['name']
        last_applied_volumeclaim['metadata']['name'] = name + '-csi'
        pvc = V1PersistentVolumeClaim(
            spec=last_applied_volumeclaim['spec'],
            metadata=last_applied_volumeclaim['metadata'],
            kind=last_applied_volumeclaim['kind'],
            api_version=last_applied_volumeclaim['apiVersion'])
        saved_old_volumeclaims.append(name)

        pvc_dict = pvc.to_dict()
        persist_resource(pvc_dict, f'{_get_resourcedir(namespace, deploy_name)}/new_pvc')
        try:
            core_v1.create_namespaced_persistent_volume_claim(namespace=ns, body=pvc)
            print(f"{Fore.GREEN} PVC {name} created.")
        except ApiException as e:
            print(f"{Fore.RED} PVC {name} wasn't created.")
            pass
    return saved_old_volumeclaims


def deployment_only_has_one_container(last_applied):
    if len(last_applied['spec']['template']['spec']['containers']) == 1:
        return True


def wait_for_creating_or_terminating(name, has_pods, resource):
    if has_pods:
        print(f'{Fore.WHITE} wait until resource is scaled to 0...')
        while has_pods:
            has_pods = _check_output(name, resource)
    elif not has_pods:
        print(f'{Fore.WHITE} wait until resource is created..')
        while not has_pods:
            has_pods = _check_output(name, resource)


def _check_output(name, resource):
    try:
        time.sleep(4.0)
        data = subprocess.check_output(f'kubectl get {resource} -n {namespace} | grep {name}', shell=True)
        print(str(data.decode('utf-8')))
        if '1/1' in str(data.decode('utf-8')):
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        print(e)


def scale_deployment_to_0(deployment_name, namespace):
    kubectl(f'scale deploy {deployment_name} --replicas=0', namespace)  # wait
    wait_for_creating_or_terminating(deployment_name, has_pods=True, resource='pods')


def _get_resourcedir(ns, deployname):
    return os.path.join(os.getcwd(), ns, deployname)


def create_resource_dir(ns, deployname):
    dirpath = _get_resourcedir(ns, deployname)
    if os.path.isdir(dirpath):
        rmtree(dirpath)
    os.makedirs(dirpath)
    return dirpath


def persist_resource(last_applied, filename):
    with open(f'{filename}.json', 'w') as file:
        json.dump(last_applied, file)


if __name__ == '__main__':
    colorama.init(autoreset=True)

    parser = argparse.ArgumentParser(description='This script migrates volumes to another storage class.')
    parser.add_argument('--namespaces', metavar='<namespace>', type=str,
                        help='the namespaces in which you want to migrate volumes. multiple namespaces are separated '
                             'by comma without any whitespaces.',
                        default='testing',
                        required=False)
    parser.add_argument('--old_storageclass', metavar='<storageclass>', type=str,
                        help='the storage class that should be replaced by another.',
                        default='testing',
                        required=True)
    parser.add_argument('--new_storageclass', metavar='<storageclass>', type=str,
                        help='the new storage class that you want to apply.',
                        default='testing',
                        required=True)
    args = parser.parse_args()

    namespaces = args.namespaces.split(',')
    old_storageclass = args.old_storageclass
    new_storageclass = args.new_storageclass

    # defaults
    dialog.want_to_start(namespaces, old_storageclass, new_storageclass)
    config.load_kube_config('~/.kube/config')
    urllib3.disable_warnings()

    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    for namespace in namespaces:
        try:
            deployments = kubectl("get Deployments -o jsonpath='{.items}'", namespace)
        except subprocess.CalledProcessError as e:
            sys.exit(0)

        for d in deployments:
            deploy_name = ''

            try:
                pvcs = [core_v1.read_namespaced_persistent_volume_claim(
                    namespace=namespace, name=vol['persistentVolumeClaim']['claimName'])
                    for vol in d['spec']['template']['spec']['volumes']]
            except KeyError as e:
                continue

            selected_volumeclaims = [pvc for pvc in pvcs if pvc.spec.storage_class_name == old_storageclass]

            if selected_volumeclaims:
                deploy_name = d['metadata']['name']
                scale_deployment_to_0(deploy_name, namespace)

                k8s_deployment = apps_v1.read_namespaced_deployment(namespace=namespace, name=deploy_name)
                last_applied_deployment = get_last_applied_deployment(k8s_deployment)
                if not last_applied_deployment:
                    print(
                        f'{Fore.RED} "last applied" not found in deployment {deploy_name}. migration was not started.')
                    continue

                resource_dir = create_resource_dir(namespace, deploy_name)
                persist_resource(last_applied_deployment, f'{resource_dir}/deployment')

                try:
                    if deployment_only_has_one_container(last_applied_deployment):
                        if dialog.want_to_proceed(deploy_name, selected_volumeclaims, new_storageclass):
                            saved_old_volumeclaims = create_csi_volumes(selected_volumeclaims, namespace, new_storageclass)
                            prepare_toolpod(namespace, saved_old_volumeclaims, deploy_name)  # mount old and new volume(s)

                            start_toolpod(namespace, deploy_name)  # rsync pod
                            modified_last_applied_deployment = replace_old_volumes_with_new(last_applied_deployment,
                                                                                            saved_old_volumeclaims)  # add mountPath and pvc
                            persist_resource(modified_last_applied_deployment, f'{resource_dir}/csi_deployment')
                            create_new_deployment(deploy_name, namespace, f'{resource_dir}/csi_deployment')  # apply to k8s
                    else:
                        print(
                            f"{Fore.RED} deployment {deploy_name} contains more than one container. "
                            f"migration was not started.")
                except:
                    print(f"{Fore.RED} migration failed. old deployment is going to applied...")
                finally:
                    create_new_deployment(deploy_name, namespace, f'{resource_dir}/csi_deployment')
