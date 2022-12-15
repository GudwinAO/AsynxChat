"""
2. Каждое из слов «class», «function», «method» записать в байтовом формате
без преобразования в последовательность кодов
не используя методы encode и decode)
и определить тип, содержимое и длину соответствующих переменных.

Подсказки:
--- b'class' - используйте маркировку b''
--- используйте списки и циклы, не дублируйте функции
"""

STR_A = b'class'
STR_B = b'function'
STR_C = b'method'

STR_LIST = [STR_A, STR_B, STR_C]

for el in STR_LIST:
    print(type(el))
    print(el)
    print(len(el))
