from services.shared.errors import ApiError


class GetOrderStatus:
    def __init__(self, order_repository):
        self.order_repository = order_repository

    def execute(self, order_id):
        order = self.order_repository.find_order_by_id(order_id)
        if not order:
            raise ApiError(404, "order_not_found", "Order not found")
        return {
            "orderId": order["order_id"],
            "status": order["status"],
            "sagaId": order["saga_id"],
            "updatedAt": order["updated_at"].isoformat() if order.get("updated_at") else None,
        }
