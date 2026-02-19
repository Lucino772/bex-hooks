from __future__ import annotations


class BexExecError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__()
        self.msg = msg


class BexPluginError(BexExecError): ...
