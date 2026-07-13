from fastapi import APIRouter

from app.vacancies.dependencies import VacancyServiceDep
from app.vacancies.schemas import VacancySchema

router = APIRouter(
    prefix="/vacancies",
    tags=["vacancies"],
)


@router.get("")
async def read_vacancies(vacancy_service: VacancyServiceDep) -> list[VacancySchema]:
    return await vacancy_service.select_vacancies()


@router.get("/vacancy_id")
async def read_tasks(vacancy_id: str, vacancy_service: VacancyServiceDep) -> VacancySchema:
    return await vacancy_service.get_by_external_id(vacancy_id)