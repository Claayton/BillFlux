"""Tests from the UserRepository class"""  # pylint: disable=E0401

from pytest import raises, mark
from sqlmodel import select
from billflux.domain.models.users import User
from billflux.infra.entities import User as UserModel
from billflux.errors import DefaultError
from tests.conftest import user


def test_insert_user(fake_user, user_repository, get_test_session):
    """
    Testing the insert_user method.
    Will be return a object of User type with the same params sends.
    """

    response = user_repository.insert_user(
        name=fake_user.name,
        email=fake_user.email,
        password_hash=fake_user.password_hash,
        secundary_id=fake_user.secundary_id,
    )

    with get_test_session as session:
        query_user = session.exec(
            select(UserModel).where(UserModel.email == fake_user.email)
        ).one()

    # Testando se as informacoes enviadas pelo metodo estao no db.
    assert isinstance(response, User)
    assert response.name == query_user.name
    assert response.email == query_user.email
    assert response.password_hash == query_user.password_hash
    assert response.secundary_id == query_user.secundary_id


@mark.parametrize(
    "email,password_hash",
    [
        (user.email, None),
        (None, user.password_hash),
    ],
)
def test_insert_user_missing_one_of_the_params(user_repository, email, password_hash):
    """
    Testing error on insert_user method.
    If one the params is not used.
    Is should return an error of type DefaultError.
    """

    with raises(DefaultError) as error:

        user_repository.insert_user(
            email=email,
            password_hash=password_hash,
        )

    assert "error" in str(error.value)


@mark.parametrize(
    "user_id,email",
    [(user.id, None), (None, user.email)],
)
def test_get_user(
    user_repository_with_one_user,
    get_test_session,
    fake_user,
    user_id,
    email,
):
    """
    Testing the get_user methods, searching by id and email.
    It should return an object of type User with all the users information.
    """

    response = user_repository_with_one_user.get_user(user_id=user_id, email=email)

    with get_test_session as session:
        query_user = session.exec(
            select(UserModel).where(UserModel.email == fake_user.email)
        ).one()

    # Testing if the informations send from the method are in database.
    assert isinstance(response, User)
    assert response.name == query_user.name
    assert response.email == query_user.email
    assert response.password_hash == query_user.password_hash
    assert response.secundary_id == query_user.secundary_id


def test_get_user_with_no_results_found(user_repository, fake_user):
    """
    Testing the get_user method, with not result founded.
    It should return an empty list.
    """

    response = user_repository.get_user(user_id=fake_user.id, email=fake_user.email)

    # Testando se o retorno e uma lista vazia.
    assert response == []


def test_get_user_without_params(user_repository):
    """
    Testing the get_user method, without params.
    It should return a DefaultError.
    """

    with raises(Exception) as error:

        user_repository.get_user(user_id=None, email=None)

    assert "error" in str(error.value)


def test_get_users(user_repository_with_one_user, fake_user, get_test_session):
    """
    Testing the get_users method.
    It should return a list with all registered users.
    """

    with get_test_session as session:
        new_user = UserModel(
            id=fake_user.id + 1,
            name=fake_user.name,
            email=f"{fake_user.email}2",
            password_hash=fake_user.password_hash,
            secundary_id=fake_user.secundary_id,
            is_staff=fake_user.is_staff,
            is_active_user=fake_user.is_active_user,
            date_joined=fake_user.date_joined,
            last_login=fake_user.last_login,
        )
        session.add(new_user)
        session.commit()

    response = user_repository_with_one_user.get_users()

    with get_test_session as session:
        query_users = list(session.exec(select(UserModel)))

    # Testing if te sended informations from the method are on database.
    assert isinstance(response, list)
    assert response[0].id == query_users[0].id
    assert response[0].email == query_users[0].email
    assert response[1].id == query_users[1].id
    assert response[1].email == query_users[1].email


def test_get_users_with_no_results_found(user_repository):
    """
    Testing the get_users method, without results.
    It should return a empty list.
    """

    response = user_repository.get_users()

    # Testando se o retorno e uma lista vazia.
    assert response == []


def test_update_user(user_repository_with_one_user, fake_user, get_test_session):
    """
    Testing the update_user method.
    It should return a object of User type with the same sended params.
    """

    with get_test_session as session:
        query_user = session.exec(
            select(UserModel).where(UserModel.id == fake_user.id)
        ).one()

    response = user_repository_with_one_user.update_user(
        user_id=fake_user.id,
        name=f"{fake_user.name}2",
        email=f"{fake_user.email}2",
        is_staff=True,
        is_active_user=True,
    )

    # Testing if the method sended informations are on database.
    assert isinstance(response, User)
    assert response.id == query_user.id
    assert response.name != query_user.name
    assert response.email != query_user.email


def test_update_user_with_no_results_found(user_repository, fake_user):
    """
    Testing the update_user method where user ID is not found on database.
    It should return a DefaultError.
    """

    with raises(DefaultError) as error:

        user_repository.update_user(
            user_id=fake_user.id,
            name=f"{fake_user.name}2",
            email=f"{fake_user.email}2",
            is_staff=True,
            is_active_user=True,
        )
    assert "Usuario nao encontrado!" in str(error.value)


@mark.parametrize(
    "user_id,email",
    [
        (user.id, user.email),
        (user.id, f"{user.email}"),
    ],
)
def test_update_user_with_email_unavailable(
    user_repository_with_one_user,
    get_test_session,
    fake_user,
    user_id,
    email,
):
    """
    Testing the update_user method, where new user name or email is unavailable.
    It should return a DefaultError.
    """

    with get_test_session as session:
        new_user = UserModel(
            id=fake_user.id + 1,
            name=fake_user.name,
            email=f"{fake_user.email}2",
            password_hash=fake_user.password_hash,
            secundary_id=fake_user.secundary_id,
            is_staff=fake_user.is_staff,
            is_active_user=fake_user.is_active_user,
            date_joined=fake_user.date_joined,
            last_login=fake_user.last_login,
        )
        session.add(new_user)
        session.commit()

    with raises(DefaultError) as error:

        user_repository_with_one_user.update_user(
            user_id=user_id,
            name=f"{fake_user.name}2",
            email=f"{fake_user.email}2",
            is_staff=True,
            is_active_user=True,
        )

    assert "indisponivel" in str(error.value)


def test_delete_user(user_repository_with_one_user, fake_user, get_test_session):
    """
    Testing the delete_user method.
    It should return a object of User type with the user deleted information.
    """

    response = user_repository_with_one_user.delete_user(fake_user.id)

    with get_test_session as session:
        query_user = session.exec(
            select(UserModel).where(UserModel.email == fake_user.email)
        ).all()

    assert isinstance(response, User)
    assert response.id == fake_user.id
    assert not query_user


def test_delete_user_with_no_results_found(user_repository, fake_user):
    """
    Testing the delete_user method where the user ID is not found on database.
    it should return a DefaultError.
    """
    with raises(DefaultError) as error:

        user_repository.delete_user(user_id=fake_user.id)

    assert "Usuario nao encontrado!" in str(error.value)
