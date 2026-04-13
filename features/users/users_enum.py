from enum import Enum

class GoalEnum(str, Enum):
    BULKING = "bulking"
    CUTTING = "cutting"
    MAINTENANCE = "maintenance"

class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class TrainingTypeEnum(str, Enum):
    HYPERTROPHY = "hypertrophy"
    STRENGTH = "strength"
    POWERBUILDING = "powerbuilding"
    ENDURANCE = "endurance"
    GENERAL_FITNESS = "general_fitness"

class ExperienceLevelEnum(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"