from abc import ABC, abstractmethod


class MfaRepository(ABC):
    @abstractmethod
    def create(self, challenge):
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, challenge_id):
        raise NotImplementedError

    @abstractmethod
    def mark_verified(self, challenge_id):
        raise NotImplementedError

