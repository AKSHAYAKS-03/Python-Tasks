import sqlite3

# ---------------- DATABASE ----------------
conn = sqlite3.connect("orm.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()


# ---------------- FIELD CLASSES ----------------
class Field:
    def __init__(self, nullable=False, unique=False):
        self.nullable = nullable
        self.unique = unique
        self.name = None

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


# inheriting field class 
class CharField(Field):
    def __init__(self, max_length=255, nullable=False, unique=False):
        super().__init__(nullable=nullable, unique=unique)
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



# Relationship field
class ForeignKey(Field):
    def __init__(self, to, related_name=None, nullable=False):
        super().__init__(nullable=nullable)
        self.to = to
        self.related_name = related_name

    def __set__(self, instance, value):
        if value is not None:
            instance.__dict__[self.name] = value
            instance.__dict__[self.name + "_id"] = value.id

    def sql(self):
        return "INTEGER"


# Oru parent object kitta irundhu, adha refer pannra child objects ellam fetch panna use aagura special object

class ReverseRelation:
    def __init__(self, model, field_name):
        self.model = model
        self.field_name = field_name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        table = self.model.__name__.lower()
        sql = f"SELECT * FROM {table} WHERE {self.field_name}_id = {instance.id};"
        print("SQL:", sql)

        cursor.execute(
            f"SELECT * FROM {table} WHERE {self.field_name}_id = ?",
            (instance.id,)
        )
        # Because Python la single value tuple create panna comma venum.
        # means tuple with one item.
        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append(self.model.from_row(row))
        return result
       #returns list of child objects related to the parent instance




# Class create aagumbodhe adha control pannra class
# cls = Current metaclass (ModelMeta)
# name =Create aagura class name
# bases =Parent classes tuple
# attrs = Class body la irukkura ellam dictionary ah varum
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

        for field_name, field in fields.items():
            if isinstance(field, ForeignKey) and field.related_name:
                setattr(field.to, field.related_name, ReverseRelation(new_class, field_name))
# Department.employees = ReverseRelation(Employee, "dept")
        return new_class

class QuerySet:
    def __init__(self, model):
        self.model = model
        self.conditions = []
        self.values = []
        self.order = ""

    def filter(self, **kwargs):
        # Multiple named values receive pannum.
        for key, value in kwargs.items():
            if "__" in key:
                field, op = key.split("__")

                if op == "gte":
                    self.conditions.append(f"{field} >= ?")
                elif op == "lte":
                    self.conditions.append(f"{field} <= ?")
                elif op == "gt":
                    self.conditions.append(f"{field} > ?")
                elif op == "lt":
                    self.conditions.append(f"{field} < ?")
                else:
                    raise ValueError("Invalid filter")

            else:
                self.conditions.append(f"{key} = ?")

            self.values.append(value)

        return self
    # for method chaining

    def order_by(self, field_name):
        if field_name.startswith("-"):
            self.order = f"ORDER BY {field_name[1:]} DESC"
        else:
            self.order = f"ORDER BY {field_name} ASC"
        return self

    def all(self):
        table = self.model.__name__.lower()
        sql = f"SELECT * FROM {table}"

        if self.conditions:
            sql += " WHERE " + " AND ".join(self.conditions)

        if self.order:
            sql += " " + self.order

        sql += ";"
        print("SQL:", sql)

        cursor.execute(sql, self.values)
        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append(self.model.from_row(row))
        return result


class Model(metaclass=ModelMeta):
    id = IntegerField(nullable=True)

    def __init__(self, **kwargs):
        self.id = kwargs.get("id")

        for field_name in self._fields:
            if field_name in kwargs:
                setattr(self, field_name, kwargs[field_name])

    @classmethod
    def create_table(cls):
        table = cls.__name__.lower()
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]

        for field_name, field in cls._fields.items():
            if isinstance(field, ForeignKey):
                col = f"{field_name}_id {field.sql()}"
            else:
                col = f"{field_name} {field.sql()}"

            if not field.nullable:
                col += " NOT NULL"

            if field.unique:
                col += " UNIQUE"

            columns.append(col)

        pretty_sql = f"CREATE TABLE IF NOT EXISTS {table} (\n       " + ",\n       ".join(columns) + "\n     );"
        print("SQL:", pretty_sql)

        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})")
        conn.commit()

        print(f"Table '{table}' created.")

    def save(self):
        table = self.__class__.__name__.lower()

        columns = []
        values = []
        placeholders = []

        for field_name, field in self._fields.items():
            if isinstance(field, ForeignKey):
                columns.append(field_name + "_id")
                values.append(self.__dict__.get(field_name + "_id"))
            else:
                columns.append(field_name)
                values.append(getattr(self, field_name))

            placeholders.append("?")

        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)});"

        printable_sql = sql
        for val in values:
            if isinstance(val, str):
                printable_sql = printable_sql.replace("?", f"'{val}'", 1)
            else:
                printable_sql = printable_sql.replace("?", str(val), 1)

        print("SQL:", printable_sql)

        cursor.execute(sql, values)
        conn.commit()

        self.id = cursor.lastrowid
        print(f"Record saved: {self.__class__.__name__}(id={self.id})")

    def delete(self):
        table = self.__class__.__name__.lower()
        sql = f"DELETE FROM {table} WHERE id = {self.id};"
        print("SQL:", sql)

        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (self.id,))
        conn.commit()

        print(f"Record deleted: {self.__class__.__name__}(id={self.id})")

    @classmethod
    def filter(cls, **kwargs):
        return QuerySet(cls).filter(**kwargs)

    @classmethod
    def all(cls):
        return QuerySet(cls).all()

    @classmethod
    def from_row(cls, row):
        data = dict(row)

        obj_data = {"id": data.get("id")}

        for field_name, field in cls._fields.items():
            if not isinstance(field, ForeignKey):
                obj_data[field_name] = data.get(field_name)

        obj = cls(**obj_data)
        obj.id = data.get("id")

        for field_name, field in cls._fields.items():
            if isinstance(field, ForeignKey):
                obj.__dict__[field_name + "_id"] = data.get(field_name + "_id")

        return obj

    def __repr__(self):
        parts = [f"id={self.id}"]

        for field_name, field in self._fields.items():
            if isinstance(field, ForeignKey):
                parts.append(f"{field_name}_id={self.__dict__.get(field_name + '_id')}")
            else:
                parts.append(f"{field_name}={repr(getattr(self, field_name))}")

        return f"{self.__class__.__name__}({', '.join(parts)})"


class User(Model):
    name = CharField(max_length=100)
    email = CharField(max_length=255, unique=True)
    age = IntegerField(nullable=True)


class Post(Model):
    title = CharField(max_length=200)
    author = ForeignKey(User, related_name="posts")


if __name__ == "__main__":
    cursor.execute("DROP TABLE IF EXISTS post")
    cursor.execute("DROP TABLE IF EXISTS user")
    conn.commit()

    User.create_table()
    Post.create_table()

    print()

    alice = User(name="Alice", email="alice@example.com", age=30)
    alice.save()

    print()

    post1 = Post(title="Hello World", author=alice)
    post1.save()

    print()

    users = User.filter(age__gte=25).order_by("-name").all()
    print(users)

    print()

    print(alice.posts)