from models.member import UserModel


def has_fortune_access(user: UserModel) -> bool:
    return bool(user.has_fortune_access)


def grant_fortune_access(user: UserModel) -> None:
    user.has_fortune_access = True


def revoke_fortune_access(user: UserModel) -> None:
    user.has_fortune_access = False
