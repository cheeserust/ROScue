from dataclasses import dataclass
from enum import Enum


class TaskAction(str, Enum):
    START   = "start"
    STOP    = "stop"
    RESTART = "restart"
    STATUS  = "status"
    PAUSE   = "pause"
    RESUME  = "resume"


@dataclass(frozen=True)
class RoscueTaskDTO:
    robot_name: str
    task_name:  str
    action:     str
    box_id:     str = ""


@dataclass(frozen=True)
class TaskResultDTO:
    accepted: bool
    message:  str = ""
