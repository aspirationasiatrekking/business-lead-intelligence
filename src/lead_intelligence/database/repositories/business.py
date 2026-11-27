from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.lead_intelligence.database.exceptions import (
    PersistenceValidationError,
)
from src.lead_intelligence.database.mappers.business import (
    business_to_complete_record,
    complete_record_to_business,
)
from src.lead_intelligence.database.models import (
    BusinessContactRecord,
    BusinessRecord,
)
from src.lead_intelligence.database.validation import validate_business_city
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.utils.country_utils import validate_country_code


class BusinessRepository:
    """Persistence operations for canonical business records."""

    def __init__(self, session: Session) -> None:
        if not isinstance(session, Session):
            raise TypeError("A SQLAlchemy Session is required.")

        self.session = session

    @staticmethod
    def _validate_id(business_id: UUID) -> None:
        if not isinstance(business_id, UUID):
            raise PersistenceValidationError("Business ID must be a UUID.")

    @staticmethod
    def _complete_record_statement():
        """Build a query that loads all required relationships."""

        return select(BusinessRecord).options(
            selectinload(
                BusinessRecord.contacts,
            ).selectinload(
                BusinessContactRecord.sources,
            ),
            selectinload(
                BusinessRecord.sources,
            ),
        )

    def create(
        self,
        business: Business,
        *,
        region: str | None = None,
    ) -> BusinessRecord:
        """Insert a complete business without committing the transaction."""

        record = business_to_complete_record(
            business,
            region=region,
        )

        self.session.add(record)

        # Execute pending SQL and populate generated identifiers.
        self.session.flush()

        return record

    def get_record_by_id(
        self,
        business_id: UUID,
    ) -> BusinessRecord | None:
        """Retrieve a complete ORM business record."""

        self._validate_id(business_id)

        statement = self._complete_record_statement().where(
            BusinessRecord.id == business_id,
        )

        return self.session.execute(
            statement,
        ).scalar_one_or_none()

    def get_by_id(
        self,
        business_id: UUID,
        *,
        region: str | None = None,
    ) -> Business | None:
        """Retrieve a complete domain business."""

        record = self.get_record_by_id(business_id)

        if record is None:
            return None

        return complete_record_to_business(
            record,
            region=region,
        )

    def exists(
        self,
        business_id: UUID,
    ) -> bool:
        """Check record existence without loading its relationships."""

        self._validate_id(business_id)

        statement = select(
            BusinessRecord.id,
        ).where(
            BusinessRecord.id == business_id,
        )

        return (
            self.session.execute(
                statement,
            ).scalar_one_or_none()
            is not None
        )

    @staticmethod
    def _location_conditions(country_code: str, city: str | None = None) -> list:
        """Build filters for actual business geography."""
        try:
            country_code = validate_country_code(country_code)
        except (TypeError, ValueError):
            raise PersistenceValidationError("Invalid country code.") from None

        conditions = [BusinessRecord.country_code == country_code]
        if city is not None:
            validate_business_city(city)
            conditions.append(
                func.lower(BusinessRecord.city) == func.lower(city.strip())
            )
        return conditions

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= 500
        ):
            raise PersistenceValidationError(
                "Limit must be an integer between 1 and 500."
            )
        if (
            not isinstance(offset, int)
            or isinstance(offset, bool)
            or not 0 <= offset <= 2_147_483_647
        ):
            raise PersistenceValidationError(
                "Offset must be a non-negative integer within the supported range."
            )

    def list_by_location(
        self,
        country_code: str,
        city: str | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Business]:
        """Retrieve a bounded page of businesses by actual location."""
        self._validate_pagination(limit, offset)
        conditions = self._location_conditions(country_code, city)
        statement = (
            self._complete_record_statement()
            .where(*conditions)
            .order_by(BusinessRecord.created_at, BusinessRecord.id)
            .limit(limit)
            .offset(offset)
        )
        records = self.session.scalars(statement).all()
        return [complete_record_to_business(record) for record in records]

    def count_by_location(self, country_code: str, city: str | None = None) -> int:
        """Count businesses matching actual geographic information."""
        conditions = self._location_conditions(country_code, city)
        statement = select(func.count()).select_from(BusinessRecord).where(*conditions)
        return self.session.execute(statement).scalar_one()

    def get_record_for_update(self, business_id: UUID) -> BusinessRecord | None:
        """Lock a business; caller must flush pending changes before calling."""
        self._validate_id(business_id)
        statement = (
            self._complete_record_statement()
            .where(BusinessRecord.id == business_id)
            .with_for_update(of=BusinessRecord)
            .execution_options(populate_existing=True)
        )
        return self.session.execute(statement).scalar_one_or_none()
