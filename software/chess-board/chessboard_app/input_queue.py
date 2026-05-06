VALID_COMMANDS = {"up", "down", "left", "right", "select"}


class InputQueue:
    def __init__(self):
        self._commands = []

    def push(self, command):
        if command not in VALID_COMMANDS:
            raise ValueError(f"unknown input command: {command}")
        self._commands.append(command)

    def drain(self):
        commands = list(self._commands)
        self._commands.clear()
        return commands
