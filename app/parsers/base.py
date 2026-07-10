from abc import ABC, abstractmethod


class AbstractParser(ABC):
    @abstractmethod
    async def get_all_vacancies(self) -> list[dict]:
        pass