class ListOffers:
    def __init__(self, offer_repository):
        self.offer_repository = offer_repository

    def execute(self):
        if hasattr(self.offer_repository, "list_active"):
            return self.offer_repository.list_active()
        return [offer for offer in self.offer_repository.list_all() if offer.get("status") == "ACTIVE"]
