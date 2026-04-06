from orm import CharField, Database, ForeignKey, IntegerField, Model


class User(Model):
    name = CharField(max_length=100)
    email = CharField(max_length=255, unique=True)
    age = IntegerField(nullable=True)


class Post(Model):
    title = CharField(max_length=200)
    author = ForeignKey(User, related_name="posts")


def main() -> None:
    Database.connect()

    User.create_table()
    Post.create_table()

    alice = User(name="Alice", email="alice@example.com", age=30)
    alice.save()

    post = Post(title="Hello World", author=alice)
    post.save()

    users = User.filter(age__gte=25).order_by("-name").all()
    print(users)

    print(alice.posts)


if __name__ == "__main__":
    main()
