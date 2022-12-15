"""
6. Создать (ПРОГРАММНО) текстовый файл test_file.txt, заполнить его тремя строками:
«сетевое программирование», «сокет», «декоратор».
Проверить кодировку файла по умолчанию.
Принудительно открыть файл в формате Unicode и вывести его содержимое.

Подсказки:
--- обратите внимание, что заполнять файл вы можете в любой кодировке
но отерыть нужно ИМЕННО в формате Unicode (utf-8)

например, with open('test_file.txt', encoding='utf-8') as t_f
невыполнение условия - минус балл
"""

NEWFILE = open('test.txt', 'w')
NEWFILE.write('сетевое программирование\nсокет\nдекоратор')
NEWFILE.close()

with open('test.txt') as codedFile:
    print(f'Кодировка файла: {codedFile.encoding}')
    for line in codedFile:
        # преобразуем содержимое в utf-8
        encd_line = line.encode('utf-8')
        # декодируем содержимое
        dcd_line = encd_line.decode('utf-8')
        print(dcd_line)