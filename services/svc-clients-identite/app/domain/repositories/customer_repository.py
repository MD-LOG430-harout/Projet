from abc import ABC, abstractmethod


class CustomerRepository(ABC):
    @abstractmethod
    def create(self, customer):
        raise NotImplementedError

    @abstractmethod
    def find_by_email(self, email):
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, customer_id):
        raise NotImplementedError

    @abstractmethod
    def set_password_hash(self, customer_id, password_hash):
        raise NotImplementedError

