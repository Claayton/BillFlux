"""Module for repository to Category (categorias de produtos)"""

from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.category import Category as CategoryModel
from billflux.domain.models.categories import Category


class CategoryRepository:
    """Category table data manipulation"""

    def insert_category(self, name: str, active: bool = True) -> Category:
        """Inserts a new category."""

        session = get_session()
        try:
            with session:
                category = CategoryModel(name=name, active=active)
                session.add(category)
                session.commit()
                session.refresh(category)
                return Category(**dict(category))
        finally:
            session.close()

    def get_categories(self) -> List[Category]:
        """Returns all categories ordered by name."""

        session = get_session()
        try:
            with session:
                sql = select(CategoryModel).order_by(CategoryModel.name)
                categories = session.exec(sql).all()
                return [Category(**dict(category)) for category in categories]
        finally:
            session.close()

    def get_active_categories(self) -> List[Category]:
        """Returns only active categories ordered by name."""

        session = get_session()
        try:
            with session:
                sql = (
                    select(CategoryModel)
                    .where(CategoryModel.active == True)  # noqa: E712
                    .order_by(CategoryModel.name)
                )
                categories = session.exec(sql).all()
                return [Category(**dict(category)) for category in categories]
        finally:
            session.close()

    def get_category(self, category_id: int) -> Optional[Category]:
        """Returns a category by its id."""

        session = get_session()
        try:
            with session:
                category = session.get(CategoryModel, category_id)
                return Category(**dict(category)) if category else None
        finally:
            session.close()

    def update_category(self, category_id: int, **fields: object) -> Optional[Category]:
        """Updates the fields of an existing category."""

        session = get_session()
        try:
            with session:
                category = session.get(CategoryModel, category_id)
                if not category:
                    return None
                for key, value in fields.items():
                    setattr(category, key, value)
                session.add(category)
                session.commit()
                session.refresh(category)
                return Category(**dict(category))
        finally:
            session.close()

    def delete_category(self, category_id: int) -> bool:
        """Deletes a category by its id."""

        session = get_session()
        try:
            with session:
                category = session.get(CategoryModel, category_id)
                if not category:
                    return False
                session.delete(category)
                session.commit()
                return True
        finally:
            session.close()

    def count_products(self, category_id: int) -> int:
        """Counts products linked to a category."""

        from billflux.infra.entities.product import Product as ProductModel

        session = get_session()
        try:
            with session:
                sql = select(ProductModel).where(
                    ProductModel.category_id == category_id
                )
                return len(session.exec(sql).all())
        finally:
            session.close()
