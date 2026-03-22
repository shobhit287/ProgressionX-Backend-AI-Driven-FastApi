from enum import Enum


class ExerciseTypeEnum(str, Enum):
    STANDARD = "standard"
    SUPERSET = "superset"
    DROPSET = "dropset"
    GIANT_SET = "giant_set"
