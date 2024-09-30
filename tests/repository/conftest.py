"""Conftest for tests/repository"""

from pytest import fixture
from sqlalchemy.exc import IntegrityError
from billflux.infra.repository import UserRepository, BillRepository
from billflux.infra.entities.bills import Bill as BillModel
from billflux.infra.entities.users import User as UserModel
from billflux.config import settings


@fixture(scope="function")
def user_repository(clean_database):  # pylint: disable=W0621
    """Fixture to mount the UserRepository object"""

    try:
        yield UserRepository(database_url=settings["testing"].DATABASE_URL)

    finally:
        clean_database  # pylint: disable=W0104


@fixture(scope="function")
def user_repository_with_one_user(
    user_repository,  # pylint: disable=W0621
    fake_user,
    get_test_session,  # pylint: disable=W0621
    clean_database,  # pylint: disable=W0621
):
    """
    Fixture to mount UserRepository object with a registered user,
    And delete the user at the end.
    """

    try:

        with get_test_session as session:
            new_user = UserModel(
                id=fake_user.id,
                name=fake_user.name,
                email=fake_user.email,
                password_hash=fake_user.password_hash,
                secundary_id=fake_user.secundary_id,
                is_staff=fake_user.is_staff,
                is_active_user=fake_user.is_active_user,
                date_joined=fake_user.date_joined,
                last_login=fake_user.last_login,
            )
            session.add(new_user)
            session.commit()

    except IntegrityError:
        ...

    try:
        yield user_repository
    finally:
        clean_database  # pylint: disable=W0104


@fixture(scope="function")
def bill_repository(clean_database):  # pylint: disable=W0621
    """Fixture to mount the BillRepository object"""

    try:
        yield BillRepository(database_url=settings["testing"].DATABASE_URL)

    finally:
        clean_database  # pylint: disable=W0104


@fixture(scope="function")
def bill_repository_with_one_bill(
    get_test_session,  # pylint: disable=W0621
    user_repository_with_one_user,  # pylint: disable=W0621
    fake_user,  # pylint: disable=W0621
    bill_repository,  # pylint: disable=W0621
    fake_bill,
    clean_database,  # pylint: disable=W0621
):
    """Fixture to show a object UserRepository whit one bill added."""

    user = user_repository_with_one_user.get_user(user_id=fake_user.id)

    try:

        with get_test_session as session:

            bill = BillModel(
                id=fake_bill.id,
                status=fake_bill.status,
                due_date=fake_bill.due_date,
                value=fake_bill.value,
                reference=fake_bill.reference,
                suplyer=fake_bill.suplyer,
                bill_type=fake_bill.bill_type,
                days=fake_bill.days,
                payday=fake_bill.payday,
                value_from_payment=fake_bill.value_from_payment,
                bar_code=fake_bill.bar_code,
                obs=fake_bill.obs,
                date_from_add=fake_bill.date_from_add,
                user_id=user.id,
            )
            session.add(bill)
            session.commit()

    except IntegrityError as error:
        raise error

    try:
        yield bill_repository
    finally:
        clean_database  # pylint: disable=W0104
