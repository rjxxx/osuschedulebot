import psycopg2
from psycopg2 import extras
import dj_database_url
from time import sleep
import sys
import traceback
from time import sleep

db_info = dj_database_url.config(
    default="postgres://DATABASE_PATH")


def connect():
    connection = psycopg2.connect(
        database=db_info.get('NAME'),
        user=db_info.get('USER'),
        password=db_info.get('PASSWORD'),
        host=db_info.get('HOST'),
        port=db_info.get('PORT')
    )
    return connection


def print_error(Exc):
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    print("PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n", Exc)


def insert_user(user_id):
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT COUNT(*) FROM "User" WHERE id=%s LIMIT 1', (user_id,))
        user = cursor.fetchone()
        if not user[0]:
            cursor.execute(
                'INSERT INTO "User" (id, id_faculty, years, id_cafedra, id_my_group, id_last_group, id_my_teacher, id_last_teacher, is_last_teacher, is_my_teacher) VALUES (%s,NULL,NULL,NULL,NULL,NULL,NULL,NULL,false,false)', (user_id,))
            connection.commit()
    except Exception as Exc:
        print_error(Exc)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_user(user_id):
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM "User" WHERE id=%s LIMIT 1;', (user_id,))
        return cursor.fetchone()
    except Exception as Exc:
        print_error(Exc)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_faculty(id_faculty=None):
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if id_faculty is None:
            cursor.execute('SELECT * FROM "Faculty";')
            return cursor.fetchall()
        else:
            cursor.execute('SELECT * FROM "Faculty" WHERE id=%s LIMIT 1;', (id_faculty,))
            return cursor.fetchone()
    except Exception as Exc:
        print_error(Exc)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_courses(id_courses=None):
    years = [(2016, "1 курс"), (2015, "2 курс"), (2014, "3 курс"), (2013, "4 курс"), (2012, "5 курс")]
    if id_courses is None:
        return years

    for year in years:
        if year[0] == id_courses:
            return year[1]

    return None


def get_groups(id_group=None, id_faculty=None, year=None):
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        if id_group is not None:
            cursor.execute('SELECT * FROM "Groups" WHERE id=%s LIMIT 1;', (id_group,))
            return cursor.fetchone()
        elif id_faculty and year is not None:
            cursor.execute('SELECT * FROM "Groups" WHERE id_faculty=%s AND years=%s;', (id_faculty, year))
            return cursor.fetchall()
        else:
            return None
    except Exception as Exc:
        print_error(Exc)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_teachers(id_teacher=None, id_cathedra=None):
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if id_teacher is not None:
            cursor.execute('SELECT * FROM "Teacher" WHERE id=%s LIMIT 1;', (id_teacher,))
            return cursor.fetchone()
        elif id_cathedra is not None:
            cursor.execute('SELECT "Rabota".id_teacher FROM "Rabota" WHERE id_cathedra=%s;', (id_cathedra,))
            teachers = cursor.fetchall()
            if not teachers:
                return None
            cursor.execute('SELECT * FROM "Teacher" WHERE "id" IN %s;', (tuple([str(key[0]) for key in teachers]),))
            return cursor.fetchall()
    except Exception as Exc:
        print_error(Exc)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_cathedra(id_cathedra=None, id_faculty=None):
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if id_cathedra is not None:
            cursor.execute('SELECT * FROM "Cathedra" WHERE id=%s LIMIT 1;', (id_cathedra,))
            return cursor.fetchone()
        elif id_faculty is not None:
            cursor.execute('SELECT * FROM "Cathedra" WHERE "Cathedra".id_faculty=%s;', (id_faculty,))
            return cursor.fetchall()
    except Exception as Exc:
        print_error(Exc)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def set_user_param(user_id, **kwargs):
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        for key, value in kwargs.items():
            cursor.execute('UPDATE "User" SET %s=%s WHERE id=%s;' % (key, value, user_id))
            connection.commit()
        connection.close()
    except Exception as Exc:
        print_error(Exc)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()