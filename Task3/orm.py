import sqlite3


def format_value(value):
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


def format_sql(sql, values):
    parts = sql.split("?")

    if not values:
        return sql + ";"

    result = []
    for index, part in enumerate(parts[:-1]):
        result.append(part)
        result.append(format_value(values[index]))

    result.append(parts[-1])
    return "".join(result) + ";"

class Database:
    @staticmethod
    def connect():
        global conn, cursor
        conn = sqlite3.connect("orm.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

class Field:
    def __init__(self, nullable=False, unique=False):
        self.nullable = nullable
        self.unique = unique

    def __set_name__(self, owner, name):
        self.name = name

    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} cannot be null")

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name)

    def __set__(self, instance, value):
        self.validate(value)
        instance.__dict__[self.name] = value

    def sql(self):
        return "TEXT"


class CharField(Field):
    def __init__(self, max_length=255, nullable=False, unique=False):
        super().__init__(nullable, unique)
        self.max_length = max_length

    def validate(self, value):
        super().validate(value)

        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{self.name} must be string")

            if len(value) > self.max_length:
                raise ValueError(f"{self.name} too long")

    def sql(self):
        return f"VARCHAR({self.max_length})"


class IntegerField(Field):
    def validate(self, value):
        super().validate(value)

        if value is not None and not isinstance(value, int):
            raise ValueError(f"{self.name} must be int")

    def sql(self):
        return "INTEGER"


class ForeignKey(Field):
    def __init__(self, to, related_name=None, nullable=False):
        super().__init__(nullable)
        self.to = to
        self.related_name = related_name

    def __set__(self, instance, value):
        if value is not None:
            instance.__dict__[self.name] = value
            instance.__dict__[self.name + "_id"] = value.id

    def sql(self):
        return "INTEGER"


class ReverseRelation:
    def __init__(self, model, field_name):
        self.model = model
        self.field_name = field_name
        #table name , foreign key column name
    def __get__(self, instance, owner):
        if instance is None:
            return self

        table = self.model.__name__.lower()
        sql = f"SELECT * FROM {table} WHERE {self.field_name}_id = ?"
        values = (instance.id,)

        print("SQL:", format_sql(sql, values))

        cursor.execute(sql, values)

        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append(self.model.from_row(row))
            #rows to objs

        return result


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name == "Model":
            return super().__new__(cls, name, bases, attrs)

        fields = {}

        for key, value in attrs.items():
            if isinstance(value, Field):
                fields[key] = value

        attrs["_fields"] = fields
        new_class = super().__new__(cls, name, bases, attrs)

        # reverse relation setup
        for field_name, field in fields.items():
            if isinstance(field, ForeignKey) and field.related_name:
                setattr(
                    field.to,
                    field.related_name,
                    ReverseRelation(new_class, field_name)
                )

        return new_class


class QuerySet:
    def __init__(self, model):
        self.model = model
        self.conditions = []
        self.values = []
        self.order = ""

    def filter(self, **kwargs):
        for key, value in kwargs.items():

            if "__" in key:
                field, op = key.split("__")

                if op == "gte":
                    condition = f"{field} >= ?"
                elif op == "lte":
                    condition = f"{field} <= ?"
                elif op == "gt":
                    condition = f"{field} > ?"
                elif op == "lt":
                    condition = f"{field} < ?"
                else:
                    raise ValueError("Invalid filter")

            else:
                condition = f"{key} = ?"

            self.conditions.append(condition)
            self.values.append(value)

        return self

    def order_by(self, field):
        if field.startswith("-"):
            self.order = f"ORDER BY {field[1:]} DESC"
        else:
            self.order = f"ORDER BY {field} ASC"

        return self

    def all(self):
        table = self.model.__name__.lower()

        sql = f"SELECT * FROM {table}"

        if self.conditions:
            sql += " WHERE " + " AND ".join(self.conditions)

        if self.order:
            sql += " " + self.order

        print("SQL:", format_sql(sql, self.values))
        cursor.execute(sql, self.values)

        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append(self.model.from_row(row))

        return result

    def __repr__(self):
        return repr(self.all())
    # print internally calls this func

class Model(metaclass=ModelMeta):
    id = IntegerField(nullable=True)

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")

        for field in self._fields:
            if field in kwargs:
                setattr(self, field, kwargs[field])

    @classmethod
    def create_table(cls):
        table = cls.__name__.lower()

        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]

        for name, field in cls._fields.items():

            if isinstance(field, ForeignKey):
                col = f"{name}_id {field.sql()}"
            else:
                col = f"{name} {field.sql()}"

            if not field.nullable:
                col += " NOT NULL"

            if field.unique:
                col += " UNIQUE"

            columns.append(col)

        sql = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})"
        print("SQL:", sql + ";")
        cursor.execute(sql)
        conn.commit()
        print(f"Table '{table}' created.")

    @classmethod
    def drop_table(cls):
        table = cls.__name__.lower()
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()

    def save(self):
        table = self.__class__.__name__.lower()

        columns = []
        values = []

        for name, field in self._fields.items():

            if isinstance(field, ForeignKey):
                columns.append(name + "_id")
                values.append(self.__dict__.get(name + "_id"))
            else:
                columns.append(name)
                values.append(getattr(self, name))

        placeholders = ["?"] * len(columns)

        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        print("SQL:", format_sql(sql, values))
        cursor.execute(sql, values)
        conn.commit()

        self.id = cursor.lastrowid
        print(f"Record saved: {self.__class__.__name__}(id={self.id})")

    def delete(self):
        table = self.__class__.__name__.lower()

        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (self.id,))
        conn.commit()

    @classmethod
    def filter(cls, **kwargs):
        return QuerySet(cls).filter(**kwargs)

    @classmethod
    def all(cls):
        return QuerySet(cls).all()

    @classmethod
    # convert a database row to a Python object
    def from_row(cls, row):
        data = dict(row)

        obj = cls(**data)

        for name, field in cls._fields.items():
            if isinstance(field, ForeignKey):
                obj.__dict__[name + "_id"] = data.get(name + "_id")

        return obj

    def __repr__(self):
        parts = [f"id={self.id}"]

        for name, field in self._fields.items():
            if isinstance(field, ForeignKey):
                value = self.__dict__.get(name + "_id")
                parts.append(f"{name}_id={value}")
            else:
                parts.append(f"{name}={repr(getattr(self, name, None))}")

        return f"{self.__class__.__name__}({', '.join(parts)})"



# # ---------------- DEMO ----------------
# if __name__ == "__main__":
#     cursor.execute("DROP TABLE IF EXISTS post")
#     cursor.execute("DROP TABLE IF EXISTS user")
#     conn.commit()

#     User.create_table()
#     Post.create_table()

#     alice = User(name="Alice", email="alice@example.com", age=30)
#     alice.save()

#     post1 = Post(title="Hello World", author=alice)
#     post1.save()

#     users = User.filter(age__gte=25).order_by("-name").all()
#     print(users)

#     print(alice.posts)
