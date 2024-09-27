"""Model for repository to User"""

from typing import Type, List
from datetime import datetime
from sqlmodel import select, create_engine
from sqlalchemy.exc import NoResultFound
from billflux.errors import DefaultError
from billflux.infra.config.database import get_session
from billflux.infra.entities.users import User as UserModel
from billflux.domain.models.users import User


class UserRepository:
    """User table data manipulation"""

    def __init__(self, database_url: str) -> None:

        self.database_url = database_url

    def __session(self):

        engine = create_engine(self.database_url)
        return get_session(engine)

    def insert_user(
        self,
        name: str = "User",
        email: str = None,
        password_hash: str = None,
        secundary_id: int = 0,  # Configurar futuramente
        is_staff: bool = False,  # Configurar futuramente
        is_active_user: bool = False,  # Configurar futuramente
        date_joined: Type[datetime] = datetime.now(),  # Configurar futuramente
        last_login: Type[datetime] = datetime.now(),
    ) -> User:
        """
        Inserts a new user into the User table.
        :param name: User name.
        :param email: User email.
        :param password_hash: Hash from the password of user.
        :param secundary_id: Secundary id from user.
        :param is_staff: If user is admin from the sistem.
        :param is_active_user: If the user is active in the sistem.
        :param date_joined: Date of the sigin on the sistem.
        :param last_login: Date of the last login in the sistem.
        :return: the insert User and your data.
        """

        with self.__session() as session:

            try:

                new_user = UserModel(
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    secundary_id=secundary_id,
                    is_staff=is_staff,
                    is_active_user=is_active_user,
                    date_joined=date_joined,
                    last_login=last_login,
                )

                session.add(new_user)
                session.commit()
                session.refresh(new_user)

                return User(**dict(new_user))

            except Exception as error:
                session.rollback()
                raise DefaultError(
                    type_error=422, message="Parametros invalidos!, error"
                ) from error

    def get_user(self, user_id: int = None, email: str = None) -> User:
        """
        Performs a search for one User registered in the system.
        The data are searching by user_id, username or email.
        :param user_id: ID from user.
        :param emil: Email from user.
        :return: One User and your data if user, or a empty list.
        """

        try:

            query_user = None

            if user_id:

                with self.__session() as session:

                    query_user = session.exec(
                        select(UserModel).where(UserModel.id == user_id)
                    ).one()

            elif email:

                with self.__session() as session:

                    query_user = session.exec(
                        select(UserModel).where(UserModel.email == email)
                    ).one()

            else:

                raise DefaultError(
                    message="""
                    E necessario o user_id ou email, para encontrar o usuario!, error""",
                    type_error=400,
                )

            return User(**dict(query_user))

        except NoResultFound:

            return []

        except Exception as error:  # pylint: disable=W0703

            raise DefaultError(message=str(error)) from error

    def get_users(self) -> List[User]:
        """
        Performs a search for all users registered in the system.
        :return: A list with all Users and their data.
        """

        with self.__session() as session:

            query_data = session.exec(select(UserModel)).all()

        response = [User(**dict(data)) for data in query_data]

        return response

    def update_user(
        self,
        user_id: int,
        name: str = None,
        email: str = None,
        password_hash: str = None,
        secundary_id: int = None,
        is_staff: bool = None,
        is_active_user: bool = None,
        date_joined: Type[datetime] = None,
        last_login: Type[datetime] = None,
    ) -> User:
        """
        Performs a update of the user data on the table User.
        :param user_id: ID from user, needed to find user in the system.
        :param name: User name.
        :param email: User email.
        :param password_hash: Hash from the password of user.
        :param secundary_id: Secundary id from user.
        :param is_staff: If user is admin from the sistem.
        :param is_active_user: If the user is active in the sistem.
        :param date_joined: Date of the sigin on the sistem.
        :param last_login: Date of the last login in the sistem.
        :return: The User with your updated data.
        """

        with self.__session() as session:

            try:

                user = session.exec(
                    select(UserModel).where(UserModel.id == user_id)
                ).one()

                if not user:

                    raise NoResultFound

            except NoResultFound as error:

                raise DefaultError(
                    message="Usuario nao encontrado!", type_error=404
                ) from error

            try:

                email_exist = session.exec(
                    select(UserModel).where(UserModel.email == email)
                ).one()

                if email_exist and user.email != email:

                    raise DefaultError(message="Email indisponivel", type_error=400)

            except NoResultFound:

                pass

            except Exception as error:

                session.rollback()
                raise DefaultError(message=str(error)) from error

            try:

                if name is not None:
                    user.name = name
                if email is not None:
                    user.email = email
                if password_hash is not None:
                    user.password_hash = password_hash
                if secundary_id is not None:
                    user.secundary_id = secundary_id
                if is_staff is not None:
                    user.is_staff = is_staff
                if is_active_user is not None:
                    user.is_active_user = is_active_user
                if date_joined is not None:
                    user.date_joined = date_joined
                if last_login is not None:
                    user.last_login = last_login

                session.commit()
                session.refresh(user)

                return User(**dict(user))

            except Exception as error:  # pylint: disable=W0703

                session.rollback()
                raise DefaultError(message=str(error)) from error

    def delete_user(self, user_id: int) -> User:
        """
        Delete a user from database.
        :param user_id: ID from user.
        :return: The deleted User and your data.
        """

        with self.__session() as session:

            try:

                user = session.exec(
                    select(UserModel).where(UserModel.id == user_id)
                ).one()

                if not user:

                    raise NoResultFound

            except NoResultFound as error:

                raise DefaultError(
                    message="Usuario nao encontrado!", type_error=404
                ) from error

            try:

                session.delete(user)
                session.commit()

                return User(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    password_hash=user.password_hash,
                    secundary_id=user.secundary_id,
                    is_staff=user.is_staff,
                    is_active_user=user.is_active_user,
                    last_login=user.last_login,
                    date_joined=user.date_joined,
                )

            except Exception as error:

                session.rollback()
                raise DefaultError(message=str(error)) from error
