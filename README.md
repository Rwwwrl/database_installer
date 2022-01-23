# Скрипт для:
- Переустановки бд, задействованных в джанго-проекте.  
- Удалить все старые файлы миграций, создать и применить новые для всех приложений в джанго-проекте.
## Установки и настройка
1. Добавить *django_reinstallation_app* в *settings.INSTALLED_APPS*:
```python
INSTALLED_APPS = (
    ...
    'django_reinstallation_app',
    ...
)
```
2. Скрипт по умолчанию берет все бд и их настройки (*name, user, host ...*) из ***settings.DATABASES***. БД должна быть ***postgres***. 
Заигнорить бд, для которой переустановку делать не надо можно, указав в *settings.py*
```python
DATABASES_TO_IGNORE = ['*']  # Заигнорить все бд, которые есть в проекте
DATABASES_TO_IGNORE = ['some_db']  # Заигнорить бд some_db (some_db - имя бд в postgres)
```  
3. Скрипт по умолчанию удаляет старые миграции, создает новые и применяет их для всех приложений, созданных пользователем в *settings.INSTALLED_APPS*  
Заигнорить приложение, для которого не нужно этого делать можно, указав в *settings.py*
```python
DJANGO_APPS_TO_IGNORE = ['*']  # Заигнорить все приложения, которые есть в проекте
DJANGO_APPS_TO_IGNORE = ['app']  # Заигнорить приложение app
```
## Запуск
Запуск скрипта реализован как джанго-комманда `python manage.py install -p -m`
***-p*** - переустановка БД
***-m*** - удаление старых миграция, создание и примение новых

