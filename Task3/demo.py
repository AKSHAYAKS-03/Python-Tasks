from orm import CharField, Database, ForeignKey, IntegerField, Model, QuerySet
import ast
#to analyze the syntax of the command entered by the user

class User(Model):
    name = CharField(max_length=100)
    email = CharField(max_length=255, unique=True)
    age = IntegerField(nullable=True)


class Post(Model):
    title = CharField(max_length=200)
    author = ForeignKey(User, related_name="posts")


def main():
    Database.connect()

    Post.drop_table()
    User.drop_table()

    User.create_table()
    Post.create_table()

    context = {
        "User": User,
        "Post": Post,
    }

    print("Type ORM commands in the terminal.")
    print("Type exit to stop.")
    print("Example: alice = User(name=\"Alice\", email=\"alice@example.com\", age=30)")

    while True:
        command = input(">> ").strip()

        if not command:
            continue

        if command.lower() == "exit":
            print("Program closed.")
            break

        try:
            parsed = ast.parse(command, mode="exec")
            is_assignment = (
                len(parsed.body) == 1 and isinstance(parsed.body[0], ast.Assign)
            )

            if is_assignment:
                target_names = []
                for target in parsed.body[0].targets:
                    if isinstance(target, ast.Name):
                        target_names.append(target.id)

                exec(command, {}, context)
                print("Saved in memory.")

                for name in target_names:
                    value = context.get(name)
                    if isinstance(value, QuerySet):
                        print(value)
            else:
                try:
                    result = eval(command, {}, context)
                    if result is not None:
                        print(result)
                except Exception as error:
                    print("Error:", error)
        except Exception as error:
            print("Error:", error)


if __name__ == "__main__":
    main()



# alice = User(name="Alice", email="alice@example.com", age=30)
# alice.save()

# bob = User(name="Bob", email="bob@example.com", age=25)
# bob.save()

# User.filter(age__gte=25)
# User.filter(name="Alice")
# q1 = User.filter(age__gte=20).order_by("-name")
# q1

# post1 = Post(title="Hello World", author=alice)
# post1.save()
# alice.posts


# User.filter(age__lt=30)
# Post.filter(title="Hello World")
# User.filter(age__gte=20).order_by("name")
# User.filter(age__gte=20).order_by("-name")
