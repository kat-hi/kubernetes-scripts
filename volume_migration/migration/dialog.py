import sys
from colorama import Fore
import colorama

colorama.init(autoreset=True)


def _input():
    while True:
        inputstring = input()
        if inputstring == 'y':
            print(f"{Fore.GREEN} proceed...")
            return True
        elif inputstring == 'n':
            print(f"{Fore.RED} aborted!")
            return False


def want_to_start(namespaces, old_storageclass, new_storageclass):
    print('######################################################')
    print(f"{Fore.YELLOW} do you really want to start? y/n \n"
          f"{Fore.WHITE} namespaces: {namespaces}\n"
          f" old storageclass: {old_storageclass}\n"
          f" new storageclass: {new_storageclass}\n")
    print('######################################################')
    if not _input():
        sys.exit(0)


def want_to_proceed(deployname, volclaims, new_storageclass):
    print('######################################################')
    print(f"{Fore.YELLOW} want to proceed? y/n\n"
          f"{Fore.WHITE} deployment name: {deployname}")
    for volclaim in volclaims:
        print(f"{Fore.WHITE} volclaim accessmode: {volclaim.spec.access_modes}\n"
              f" volclaim old / new storageclass: {volclaim.spec.storage_class_name} -> {new_storageclass}")
    print('######################################################')
    if _input():
        return True
