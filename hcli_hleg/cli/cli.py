import json
import io
import service

from hcli_hleg import config


class CLI:
    commands = None
    inputstream = None
    service = None

    def __init__(self, commands, inputstream):
        self.commands = commands
        self.inputstream = inputstream
        self.service = service.Service()

    def execute(self):

        if self.commands[1] == "ls":
            ls = json.dumps(self.service.ls(), indent=4) + "\n"

            return io.BytesIO(ls.encode("utf-8"))

        return None
