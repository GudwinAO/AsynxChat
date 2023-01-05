"""Лаунчер"""

import subprocess

PROCESSES = []

while True:
    ACTION = input('Выберите действие: q - выход, '
                   's - запустить сервер и клиенты, x - закрыть все окна: ')

    if ACTION == 'q':
        break

    elif ACTION == 's':
        PROCESSES.append(subprocess.Popen('python server.py',
                                          shell=True))
        PROCESSES.append(subprocess.Popen('python client.py -n test1',
                                          shell=True))
        PROCESSES.append(subprocess.Popen('python client.py -n test2',
                                          shell=True))
        PROCESSES.append(subprocess.Popen('python client.py -n test3',
                                          shell=True))

    elif ACTION == 'x':
        while PROCESSES:
            VICTIM = PROCESSES.pop()
            VICTIM.kill()