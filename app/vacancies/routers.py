from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi_pagination import Page

from app.core.enums import Status as VacancyStatusEnum
from app.vacancies.dependencies import VacancyServiceDep, VacancySyncServiceDep
from app.vacancies.schemas import VacancySchema, VacancyFilterParams, VacancySortParams
from app.vacancies.services import VacancyNotFoundError

router = APIRouter(
    prefix="/vacancies",
    tags=["vacancies"],
)


@router.get("")
async def read_vacancies(
    vacancy_service: VacancyServiceDep,
    filters: Annotated[VacancyFilterParams, Depends(VacancyFilterParams)],
    sort: Annotated[VacancySortParams, Depends(VacancySortParams)],
) -> Page[VacancySchema]:
    return await vacancy_service.select_vacancies(filters, sort)


@router.get("/{external_id}")
async def read_vacancy(
    external_id: int, vacancy_service: VacancyServiceDep
) -> VacancySchema:
    try:
        return await vacancy_service.get_by_external_id(external_id)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.patch("/{external_id}/status")
async def change_status(
    external_id: int, new_status: VacancyStatusEnum, vacancy_service: VacancyServiceDep
) -> VacancySchema:
    try:
        return await vacancy_service.change_status(external_id, new_status)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/sync_all")
async def synchronize_vacancies(
    vacancy_service: VacancySyncServiceDep,
) -> dict:
    return await vacancy_service.sync_all()
