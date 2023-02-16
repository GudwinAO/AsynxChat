from setuptools import setup, find_packages

setup(name='client_chat_pyqt',
      version='0.1',
      description='Client part',
      packages=find_packages(),  # ,Будем искать пакеты тут(включаем авто поиск пакетов)
      author_email='gudwinao88@gmail.com',
      author='Aleksandr Osipov',
      install_requeres=['PyQt5', 'sqlalchemy', 'pycruptodome', 'pycryptodomex']
      ##зависимости 
      )
