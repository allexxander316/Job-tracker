from fastapi import APIRouter, HTTPException, status

from app.vacancies.dependencies import VacancyServiceDep
from app.vacancies.schemas import VacancySchema, ChangeStatusSchema
from app.vacancies.services import VacancyNotFoundError

router = APIRouter(
    prefix="/vacancies",
    tags=["vacancies"],
)


@router.get("")
async def read_vacancies(vacancy_service: VacancyServiceDep) -> list[VacancySchema]:
    return await vacancy_service.select_vacancies()


@router.get("/{vacancy_id}")
async def read_vacancy(
    vacancy_id: int, vacancy_service: VacancyServiceDep
) -> VacancySchema:
    try:
        return await vacancy_service.get_by_external_id(vacancy_id)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.patch("/{vacancy_id}/status")
async def change_status(
    vacancy_id: int, payload: ChangeStatusSchema, vacancy_service: VacancyServiceDep
) -> VacancySchema:
    try:
        return await vacancy_service.change_status(vacancy_id, payload)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
