from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi_pagination import Page, Params

from app.core.enums import Status as VacancyStatusEnum
from app.vacancies.dependencies import VacancyServiceDep
from app.vacancies.schemas import (
    VacancySchema,
    VacancyFilterParams,
    VacancySortParams,
    VacancyChangeSchema,
)
from app.vacancies.services import VacancyNotFoundError, VacancySyncService
from app.vacancies.sync_status import sync_tracker

router = APIRouter(
    prefix="/vacancies",
    tags=["vacancies"],
)


@router.get("")
async def read_vacancies(
    vacancy_service: VacancyServiceDep,
    filters: Annotated[VacancyFilterParams, Depends(VacancyFilterParams)],
    sort: Annotated[VacancySortParams, Depends(VacancySortParams)],
    params: Annotated[Params, Depends(Params)],
) -> Page[VacancySchema]:
    return await vacancy_service.select_vacancies(filters, sort, params)


@router.get("/sync/status")
async def sync_status() -> dict | None:
    return sync_tracker.get()


@router.get("/{vacancy_id}")
async def read_vacancy(
    vacancy_id: int, vacancy_service: VacancyServiceDep
) -> VacancySchema:
    try:
        return await vacancy_service.get_by_id(vacancy_id)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.patch("/{vacancy_id}/status")
async def change_status(
    vacancy_id: int, new_status: VacancyStatusEnum, vacancy_service: VacancyServiceDep
) -> VacancySchema:
    try:
        return await vacancy_service.change_status(vacancy_id, new_status)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post(
    "/sync_all",
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {"description": "Sync already running"}},
)
async def synchronize_vacancies(background_tasks: BackgroundTasks) -> dict:
    if sync_tracker.is_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Sync already running"
        )

    background_tasks.add_task(VacancySyncService.run_sync_in_background)
    return {"message": "sync started"}


@router.get("/{vacancy_id}/changes")
async def read_vacancy_changes(
    vacancy_id: int, vacancy_service: VacancyServiceDep
) -> list[VacancyChangeSchema]:
    try:
        return await vacancy_service.get_changes(vacancy_id)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/{vacancy_id}/acknowledge_changes")
async def acknowledge_vacancy_changes(
    vacancy_id: int, vacancy_service: VacancyServiceDep
) -> VacancySchema:
    try:
        return await vacancy_service.acknowledge_changes(vacancy_id)
    except VacancyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
