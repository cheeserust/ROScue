from dataclasses import dataclass


class TaskAction(str, str):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    STATUS = "status"


@dataclass(frozen=True)
class RoscueTaskDTO:
    robot_name: str
    task_name: str
    action: TaskAction


@dataclass(frozen=True)
class TaskResultDTO:
    accepted: bool
    message: str = ""