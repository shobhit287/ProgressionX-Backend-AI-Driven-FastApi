from enum import Enum

class GoalEnum(str, Enum):
    BULKING = "bulking"
    CUTTING = "cutting"
    MAINTENANCE = "maintenance"

class GenderEnum(str,Enum):
    MALE = "male"
    FEMALE= "female"
    OTHER= "other"