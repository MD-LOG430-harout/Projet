class MockHlrAdapter:
    def __init__(self, force_failure=False):
        self.force_failure = force_failure

    def provision(self, line, trace_id=None):
        if self.force_failure:
            raise RuntimeError("mock HLR failure")
        return True
