"""File to Hash the password"""

import bcrypt  # pylint: disable=E0401


class PasswordHash:
    """Class responsible for hashing user password"""

    @staticmethod
    def hash(password: str) -> str:
        """Performs the password hashing process"""

        hashed = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

        return hashed

    @staticmethod
    def verify(password: str, password_hashed: str) -> bool:
        """Checks that the password passed in the same as the password entered"""

        is_hashed = (
            bcrypt.hashpw(password.encode("utf8"), password_hashed) == password_hashed
        )

        return is_hashed
