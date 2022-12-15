"""
6. Создать текстовый файл test_file.txt, заполнить его тремя строками:
«сетевое программирование», «сокет», «декоратор».
Проверить кодировку файла по умолчанию.
Принудительно открыть файл в формате Unicode и вывести его содержимое.

Подсказки:
--- обратите внимание, что заполнять файл вы можете в любой кодировке
но отерыть нужно ИМЕННО в формате Unicode (utf-8)

например, with open('test_file.txt', encoding='utf-8') as t_f
невыполнение условия - минус балл
"""

from chardet import detect

LINES_LST = ['сетевое программирование', 'сокет', 'декоратор']
with open('test.txt', 'w') as file:
    for line in LINES_LST:
        file.write(f'{line}\n')
file.close()

# узнаем кодировку файла
with open('test.txt', 'rb') as file:
    CONTENT = file.read()
ENCODING = detect(CONTENT)['encoding']
print(ENCODING)

# открываем файл в правильной кодировке
with open('test.txt', 'r', encoding=ENCODING) as file:
    CONTENT = file.read()
print(CONTENT)
