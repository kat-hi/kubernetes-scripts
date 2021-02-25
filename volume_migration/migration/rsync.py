old_new_pathmapper = {'/mnt/old/0': '/data/db'}
mountpaths = [{'mountPath': '/data/db', 'name': 'mongo-pvc-test'}]
import subprocess
import sys
import os
from shutil import copyfile

OLD_MOUNTPATH = '/mnt/old'
LOGFILE = 'rsynclog.txt'


def check_if_sync_complete(mountpath):
    with open(f'{mountpath}/{LOGFILE}', 'r') as log:
        logs = log.read()

    if len(logs) == subdir_count + 1:
        print('remove rsynclog')
        #os.remove('/mnt/new/rsynclog.txt')
    else:
        with open(f'{OLD_MOUNTPATH}/{LOGFILE}', 'a+') as log:
            print('synced dir count does not match')
            log.write(f'subdircount: {subdir_count}\nlog_length: {len(logs) - 1}')


def remove_logfiles_if_exist(new_mountpath):
    if os.path.isfile(f'{OLD_MOUNTPATH}/{LOGFILE}'):
        os.remove(f'{OLD_MOUNTPATH}/{LOGFILE}')
        print(f'{OLD_MOUNTPATH}/{LOGFILE} removed')
    if os.path.isfile(f'{new_mountpath}/{LOGFILE}'):
        os.remove(f'{new_mountpath}/{LOGFILE}')
        print(f'{new_mountpath}/{LOGFILE} removed')


def sync(subdir):
    old_dir = f'{OLD_MOUNTPATH}/{subdir}'
    print(f'starting rsync for contents in subdir {old_dir} into {old_new_pathmapper[old_dir]}')
    subprocess.run(f'rsync -a -v {old_dir}/ {old_new_pathmapper[old_dir]}', shell=True)
    log.write(str(i))
    print(f'rsync finished: {old_dir}')


if __name__ == '__main__':

    for mountpath in mountpaths:
        remove_logfiles_if_exist(mountpath['mountPath'])

    with open(f'{OLD_MOUNTPATH}/{LOGFILE}', 'a+') as log:
        log.write('.')

        subdirs = [os.path.join(OLD_MOUNTPATH, str(i)) for i in range(0, 50)
                   if os.path.isdir(os.path.join(OLD_MOUNTPATH, str(i)))]

        subdir_count = len(subdirs)
        if subdir_count == len(mountpaths):
            print('len(old_mounts) equals len(new_mounts)')
            try:
                for i in range(0, subdir_count):
                    sync(i)
            except Exception:
                pass

    for path in mountpaths:
        print(f'copyfile for {path["mountPath"]}')
        copyfile(f'{OLD_MOUNTPATH}/{LOGFILE}', f'{path["mountPath"]}/{LOGFILE}')
        print(f'check if sync complete for {path["mountPath"]}')
        check_if_sync_complete(path['mountPath'])
    sys.exit(0)
