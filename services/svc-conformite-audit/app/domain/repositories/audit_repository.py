from abc import ABC, abstractmethod


class AuditRepository(ABC):
    @abstractmethod
    def append(self, event):
        raise NotImplementedError

    @abstractmethod
    def list_by_trace_id(self, trace_id):
        raise NotImplementedError
