import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED
from collections import namedtuple
from typing import List, Union

from . import print_tool as p

from django.conf import settings

# db_django_name - значение db в словаре settings.DATABASES (пример "default"),
# db_postgres_name - значение db['NAME'] в словаре settings.DATABASES (пример "test"),
DB_SETTING_DATA = namedtuple("DB_SETTING_DATA", ["db_django_name", "db_postgres_name"])


class DbTool:
    """
    Класс для работы с базой данных, синглтон
    """

    db_connections = []

    def __new__(cls, db_name, *args, **kwargs):
        cls.databases_used_in_project = cls.__get_used_databases_in_project()
        cls.available_databases = list(
            filter(lambda db: not cls.is_this_db_in_ignore(db.db_postgres_name), cls.databases_used_in_project)
        )

        for db_connection in cls.db_connections:
            if db_connection.connect_data["database"] == db_name:
                return db_connection
        new_db_connection_instance = super().__new__(cls)
        cls.db_connections.append(new_db_connection_instance)
        return new_db_connection_instance

    def __init__(
        self,
        db_name,
        db_user: str = "postgres",
        db_host: str = "localhost",
        db_port: str = "5432",
        password: str = None,
    ) -> None:
        connect_data = self.__get_bd_info_by_django_settings(db_name)
        if connect_data:
            self.connect_data = connect_data
        else:
            self.connect_data = {
                "database": db_name,
                "user": db_user,
                "host": db_host,
                "port": db_port,
                "password": password,
            }

    def __enter__(self):
        self.__conn = psycopg2.connect(**self.connect_data)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Если во время транзация произошла ошибка - делаем роллбек else коммит
        if exc_type:
            self.__conn.rollback()
        else:
            self.__conn.commit()
        self.__conn.close()

    def exec_request(self, sql_string: str, is_isolate_required: bool = False) -> None:
        """
        выполнить sql запрос
        """
        cursor = self.__conn.cursor()
        # для "CREATE DATABASE" и "DROP DATABASE" нужно установить в автокоммит
        if is_isolate_required:
            self.__conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        else:
            self.__conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        try:
            cursor.execute(sql_string)
        except psycopg2.Error as e:
            p.error(sql_string)
            raise e

        p.success(sql_string)
        cursor.close()

    def check_is_user_connected_to_free_db(func):
        """
        для удаления и создания БД мы должны быть подключены в бд "postgres"
        иначе будет ошибка
        """

        def inner(self_instance, *args, **kwargs):
            if self_instance.connect_data["database"] in self_instance.available_databases:
                p.error("Вы пытаетесь удалить или создать бд подключившись к одной из этих баз данных")
                raise SystemError
            return func(self_instance, *args, **kwargs)

        return inner

    @staticmethod
    def __get_used_databases_in_project() -> List[tuple[str, str]]:
        """
        получить спосок используемых бд в проекте
        """
        database_dict = settings.DATABASES
        databases_in_project = []
        for db in database_dict:
            # Мы работаем только с постгресом
            if database_dict[db]["ENGINE"] == "django.db.backends.postgresql_psycopg2":
                db_data = DB_SETTING_DATA(db, database_dict[db]["NAME"])
                databases_in_project.append(db_data)
        return databases_in_project

    def __get_bd_info_by_django_settings(self, db_name: str) -> Union[dict[str, str], None]:
        """
        получить все настройки для бд из файла settings, чтобы не дублировать их
        """
        for db in self.databases_used_in_project:
            if db.db_postgres_name == db_name:
                p.info("Была найдены настройки бд в джанго проекте, эти настройки и будут использованы для подключения")
                db_config = settings.DATABASE[db.db_django_name]
                return {
                    "database": db_name,
                    "user": db_config.get("USER", "postgres"),
                    "host": db_config.get("HOST", "localhost"),
                    "port": db_config.get("PORT", "5432"),
                    "password": db_config.get("PASSWORD", None),
                }
        p.info(
            f"Не было найдено настроек для бд '{db_name}' в settings.DATABASES, будут использованы настройки, которые вы передали в экземляр"
        )

    @staticmethod
    def is_this_db_in_ignore(db_name: str) -> bool:
        """
        проверить, находится ли бд с имененем db_name в списке игнора для переустановки
        ( в setttings.DATABASES_TO_IGNORE )
        """
        databases_to_ignore = getattr(settings, "DATABASES_TO_IGNORE", [])
        return databases_to_ignore == ["*"] or db_name in databases_to_ignore

    @check_is_user_connected_to_free_db
    def drop_project_databases(self) -> None:
        """
        удалить все базы данных, которые есть в проекте
        """
        sql_string = "DROP DATABASE IF EXISTS {};"
        for db in self.available_databases:
            self.exec_request(sql_string.format(db.db_postgres_name), is_isolate_required=True)
        if self.available_databases:
            p.info(f"Были удалены эти БД: {[db.db_postgres_name for db in self.available_databases]}")
        else:
            p.info("Не было удалено ни одной БД")

    @check_is_user_connected_to_free_db
    def create_project_databases(self) -> None:
        """
        создать пустые базы данных? которые есть в проекте
        """
        sql_string = "CREATE DATABASE {};"
        for db in self.available_databases:
            self.exec_request(sql_string.format(db.db_postgres_name), is_isolate_required=True)
        if self.available_databases:
            p.info(f"Были созданы эти БД: {[db.db_postgres_name for db in self.available_databases]}")
        else:
            p.info("Не было создано ни одной БД")
