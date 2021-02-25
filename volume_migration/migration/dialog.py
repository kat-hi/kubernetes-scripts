import sys
from colorama import Fore
import colorama

colorama.init(autoreset=True)

def want_to_proceed():
    try:
        mode = sys.argv[1]
        if mode == '-a':
            print(f"{Fore.RED} do you really want to proceed? "
                  f"this is not a testing mode. you are going to search and change pvc in all namespaces. y/n")
        elif mode == '-n':
            print(f"{Fore.RED} do you really want to proceed? "
                  f"this is not a testing mode. you are going to search and change pvc in the listed namespaces. y/n")
        while True:
            input = input()
            if input == 'y':
                print(f"{Fore.GREEN} proceed...")
                testing = False
                break
            elif input == 'n':
                print(f"{Fore.RED} aborted!")
                sys.exit()
    except IndexError:
        # no arguments = testing mode
        print(f"{Fore.GREEN} use testing mode")