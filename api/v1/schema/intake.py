import graphene
from graphene import ObjectType, Int, Float, List, Argument, String
from api.v1.db import db

# from schema.animal import AnimalType
# from schema.milk import MilkType
from api.v1.schema.bodyweight import BodyWeightType
from api.v1.schema.diet import DietType
from api.v1.schema.gas import GasType
from api.v1.schema.digestibility import DigestibilityType

class IntakeType(ObjectType):
    animalIdentifier = Int(description="Animal ID number")
    experimentCode = Int(description="Experiment code")
    experimentalDesign = Int(description="Experimental design type")
    treatmentCode = Int(description="Treatment group")
    periodNumber = Int(description="Period number")
    day = Int(description="Day number")
    dryMatterIntake = Float(description="Dry matter intake (kg/day)")

    animal = List(
        "api.v1.schema.animal.AnimalType",
        parity=Argument(Int),
        min_parity=Argument(Int),
        max_parity=Argument(Int),
        breed=Argument(Int),
        breeds=Argument(List(Int)),
        animal_status=Argument(String),
        cannulation=Argument(String),
        housing=Argument(String),
        min_days_in_milk=Argument(Int),
        max_days_in_milk=Argument(Int),
        research_identifier=Argument(String),
        contains_research=Argument(String),
        limit=Argument(Int, description="Limit number of animal records")
    )

    milk = List(
        # MilkType,
        "api.v1.schema.milk.MilkType",
        day=Argument(Int),
        milkProduction=Argument(Float),
        min_milkProduction=Argument(Float),
        max_milkProduction=Argument(Float),
        limit=Argument(Int)
    )

    bodyweight = List(
        BodyWeightType,
        day=Argument(Int),
        bodyWeight=Argument(Float),
        weightGain=Argument(Float),
        min_bodyWeight=Argument(Float),
        max_bodyWeight=Argument(Float),
        limit=Argument(Int)
    )

    diet = List(
        DietType,
        day=Argument(Int),
        crudeProteinOfDryMatter=Argument(Float),
        min_crudeProteinOfDryMatter=Argument(Float),
        max_crudeProteinOfDryMatter=Argument(Float),
        limit=Argument(Int)
    )

    gas = List(
        GasType,
        day=Argument(Int),
        methane=Argument(Float),
        carbonDioxide=Argument(Float),
        limit=Argument(Int)
    )

    digestibility = List(
        DigestibilityType,
        day=Argument(Int),
        grossEnergyDigestibility=Argument(Float),
        dryMatterDigestibility=Argument(Float),
        min_grossEnergyDigestibility=Argument(Float),
        max_grossEnergyDigestibility=Argument(Float),
        limit=Argument(Int)
    )

    def resolve_animal(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        return list(db.animal.find(query).limit(kwargs.get("limit") or 0))

    def resolve_milk(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        if "day" in kwargs:
            query["day"] = kwargs["day"]
        if "milkProduction" in kwargs:
            query["milkProduction"] = kwargs["milkProduction"]
        if kwargs.get("min_milkProduction") or kwargs.get("max_milkProduction"):
            query["milkProduction"] = {}
            if kwargs.get("min_milkProduction"):
                query["milkProduction"]["$gte"] = kwargs["min_milkProduction"]
            if kwargs.get("max_milkProduction"):
                query["milkProduction"]["$lte"] = kwargs["max_milkProduction"]
        return list(db.milk.find(query).limit(kwargs.get("limit") or 0))

    def resolve_bodyweight(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        if "day" in kwargs:
            query["day"] = kwargs["day"]
        for field in ["bodyWeight", "weightGain"]:
            if field in kwargs:
                query[field] = kwargs[field]
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if kwargs.get(min_key) or kwargs.get(max_key):
                query[field] = {}
                if kwargs.get(min_key):
                    query[field]["$gte"] = kwargs[min_key]
                if kwargs.get(max_key):
                    query[field]["$lte"] = kwargs[max_key]
        return list(db.bodyweight.find(query).limit(kwargs.get("limit") or 0))

    def resolve_diet(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        if "day" in kwargs:
            query["day"] = kwargs["day"]
        if "crudeProteinOfDryMatter" in kwargs:
            query["crudeProteinOfDryMatter"] = kwargs["crudeProteinOfDryMatter"]
        if kwargs.get("min_crudeProteinOfDryMatter") or kwargs.get("max_crudeProteinOfDryMatter"):
            query["crudeProteinOfDryMatter"] = {}
            if kwargs.get("min_crudeProteinOfDryMatter"):
                query["crudeProteinOfDryMatter"]["$gte"] = kwargs["min_crudeProteinOfDryMatter"]
            if kwargs.get("max_crudeProteinOfDryMatter"):
                query["crudeProteinOfDryMatter"]["$lte"] = kwargs["max_crudeProteinOfDryMatter"]
        return list(db.diet.find(query).limit(kwargs.get("limit") or 0))

    def resolve_gas(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        if "day" in kwargs:
            query["day"] = kwargs["day"]
        for field in ["methane", "carbonDioxide"]:
            if field in kwargs:
                query[field] = kwargs[field]
        return list(db.gasmeasurement.find(query).limit(kwargs.get("limit") or 0))

    def resolve_digestibility(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        if "day" in kwargs:
            query["day"] = kwargs["day"]
        for field in ["grossEnergyDigestibility", "dryMatterDigestibility"]:
            if field in kwargs:
                query[field] = kwargs[field]
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if kwargs.get(min_key) or kwargs.get(max_key):
                query[field] = {}
                if kwargs.get(min_key):
                    query[field]["$gte"] = kwargs[min_key]
                if kwargs.get(max_key):
                    query[field]["$lte"] = kwargs[max_key]
        return list(db.digestibility.find(query).limit(kwargs.get("limit") or 0))

class IntakeQuery(ObjectType):
    intake = List(
        IntakeType,
        animalIdentifier=Argument(Int),
        day=Argument(Int),
        dryMatterIntake=Argument(Float),
        min_dryMatterIntake=Argument(Float),
        max_dryMatterIntake=Argument(Float),
        limit=Argument(Int, description="Limit number of intake records"),
        description="Query intake data by animal, day, or intake values"
    )

    def resolve_intake(self, info, **kwargs):
        query = {}
        for field in ["animalIdentifier", "day", "dryMatterIntake"]:
            if field in kwargs:
                query[field] = kwargs[field]
        if kwargs.get("min_dryMatterIntake") or kwargs.get("max_dryMatterIntake"):
            query["dryMatterIntake"] = {}
            if kwargs.get("min_dryMatterIntake"):
                query["dryMatterIntake"]["$gte"] = kwargs["min_dryMatterIntake"]
            if kwargs.get("max_dryMatterIntake"):
                query["dryMatterIntake"]["$lte"] = kwargs["max_dryMatterIntake"]
        if kwargs.get("limit"):
            return list(db.intake.find(query).limit(kwargs.get("limit")))
        return list(db.intake.find(query))
