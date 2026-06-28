from services.shared.errors import ApiError


class GetOffer:
    def __init__(self, offer_repository):
        self.offer_repository = offer_repository

    def execute(self, offer_id):
        offer = self.offer_repository.find_by_id(offer_id)
        if not offer:
            raise ApiError(404, "offer_not_found", "Offer not found", {"offerId": offer_id})
        return offer
