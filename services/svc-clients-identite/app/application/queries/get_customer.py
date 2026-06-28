from services.shared.errors import ApiError


class GetCustomer:
    def __init__(self, customer_repository):
        self.customer_repository = customer_repository

    def execute(self, customer_id):
        customer = self.customer_repository.find_by_id(customer_id)
        if not customer:
            raise ApiError(404, "customer_not_found", "Customer not found")
        return customer
