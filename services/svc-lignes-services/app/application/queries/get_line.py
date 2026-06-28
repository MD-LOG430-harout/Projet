from services.shared.errors import ApiError


class GetLine:
    def __init__(self, line_repository):
        self.line_repository = line_repository

    def execute(self, line_id):
        line = self.line_repository.find_by_id(line_id)
        if not line:
            raise ApiError(404, "line_not_found", "Line not found", {"lineId": line_id})
        return line


class GetLineByMsisdn:
    def __init__(self, line_repository):
        self.line_repository = line_repository

    def execute(self, msisdn):
        line = self.line_repository.find_by_msisdn(msisdn)
        if not line:
            raise ApiError(404, "line_not_found", "Line not found", {"msisdn": msisdn})
        return line
