import graphene
from graphene import ObjectType, Int, String, Float, List, Argument
from api.v1.db import db

# from schema.animal import AnimalType
# from schema.intake import IntakeType
from api.v1.schema.bodyweight import BodyWeightType
from api.v1.schema.diet import DietType
from api.v1.schema.gas import GasType
from api.v1.schema.digestibility import DigestibilityType
# from graphene import LazyType


class MilkType(ObjectType):
    animalIdentifier = Int(description="Animal ID number")
    experimentCode = Int(description="Experiment code")
    experimentalDesign = Int(description="Experimental design type")
    treatmentCode = Int(description="Treatment group")
    periodNumber = Int(description="Period number in experiment")
    day = Int(description="Day number")
    milkProduction = Float(description="Daily milk production (kg)")
    milkCrudeProtein = Float(description="Milk crude protein content (g/kg)")
    milkCrudeFat = Float(description="Milk crude fat content (g/kg)")
    milkLactose = Float(description="Milk lactose content (g/kg)")

    animal = List(
        # lambda: __import__('schema.animal', fromlist=['AnimalType']).AnimalType,
        # LazyType("schema.animal.AnimalType"),
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
        limit=Argument(Int, description="Limit number of animal records returned")
    )

    intake = List(
        # IntakeType,
        "api.v1.schema.intake.IntakeType",
        day=Argument(Int),
        dryMatterIntake=Argument(Float),
        min_dryMatterIntake=Argument(Float),
        max_dryMatterIntake=Argument(Float),
        limit=Argument(Int),
        description="Intake records related to this milk sample"
    )

    bodyweight = List(
        BodyWeightType,
        day=Argument(Int),
        bodyWeight=Argument(Float),
        weightGain=Argument(Float),
        min_bodyWeight=Argument(Float),
        max_bodyWeight=Argument(Float),
        min_weightGain=Argument(Float),
        max_weightGain=Argument(Float),
        limit=Argument(Int),
        description="Bodyweight records related to this milk sample"
    )

    diet = List(
        DietType,
        day=Argument(Int),
        crudeProteinOfDryMatter=Argument(Float),
        crudeFatContentOfDryMatter=Argument(Float),
        neutralDetergentFiberContentOfDryMatter=Argument(Float),
        organicMatterContentOfDryMatter=Argument(Float),
        min_crudeProteinOfDryMatter=Argument(Float),
        max_crudeProteinOfDryMatter=Argument(Float),
        limit=Argument(Int),
        description="Diet data related to this milk sample"
    )

    gas = List(
        GasType,
        day=Argument(Int),
        methane=Argument(Float),
        carbonDioxide=Argument(Float),
        methaneMeasurementMethod=Argument(Int),
        durationOfMeasurement=Argument(Int),
        min_methane=Argument(Float),
        max_methane=Argument(Float),
        min_carbonDioxide=Argument(Float),
        max_carbonDioxide=Argument(Float),
        limit=Argument(Int),
        description="Gas records related to this milk sample"
    )

    digestibility = List(
        DigestibilityType,
        day=Argument(Int),
        grossEnergyDigestibility=Argument(Float),
        dryMatterDigestibility=Argument(Float),
        min_grossEnergyDigestibility=Argument(Float),
        max_grossEnergyDigestibility=Argument(Float),
        min_dryMatterDigestibility=Argument(Float),
        max_dryMatterDigestibility=Argument(Float),
        limit=Argument(Int),
        description="Digestibility data related to this milk sample"
    )

    def resolve_animal(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}

        if kwargs.get("parity") is not None:
            query["parity"] = kwargs["parity"]
        else:
            parity_range = {}
            if kwargs.get("min_parity"):
                parity_range["$gte"] = kwargs["min_parity"]
            if kwargs.get("max_parity"):
                parity_range["$lte"] = kwargs["max_parity"]
            if parity_range:
                query["parity"] = parity_range

        if kwargs.get("breed"):
            query["breed"] = kwargs["breed"]
        elif kwargs.get("breeds"):
            query["breed"] = {"$in": kwargs["breeds"]}

        if kwargs.get("animal_status"):
            query["animalStatus"] = kwargs["animal_status"]
        if kwargs.get("cannulation"):
            query["cannulation"] = kwargs["cannulation"]
        if kwargs.get("housing"):
            query["housing"] = kwargs["housing"]

        dim_range = {}
        if kwargs.get("min_days_in_milk"):
            dim_range["$gte"] = kwargs["min_days_in_milk"]
        if kwargs.get("max_days_in_milk"):
            dim_range["$lte"] = kwargs["max_days_in_milk"]
        if dim_range:
            query["daysInMilk"] = dim_range

        if kwargs.get("research_identifier"):
            query["researchIdentifier"] = kwargs["research_identifier"]
        elif kwargs.get("contains_research"):
            query["researchIdentifier"] = {"$regex": kwargs["contains_research"], "$options": "i"}

        if kwargs.get("limit"):
            return list(db.animal.find(query).limit(kwargs.get("limit")))
        return list(db.animal.find(query))

    def resolve_intake(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        if "day" in kwargs:
            query["day"] = kwargs["day"]
        if "dryMatterIntake" in kwargs:
            query["dryMatterIntake"] = kwargs["dryMatterIntake"]
        if kwargs.get("min_dryMatterIntake") or kwargs.get("max_dryMatterIntake"):
            query["dryMatterIntake"] = {}
            if kwargs.get("min_dryMatterIntake"):
                query["dryMatterIntake"]["$gte"] = kwargs["min_dryMatterIntake"]
            if kwargs.get("max_dryMatterIntake"):
                query["dryMatterIntake"]["$lte"] = kwargs["max_dryMatterIntake"]
        if kwargs.get("limit"):
            return list(db.intake.find(query).limit(kwargs.get("limit")))
        return list(db.intake.find(query))

    def resolve_bodyweight(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        for field in ["day", "bodyWeight", "weightGain"]:
            if field in kwargs:
                query[field] = kwargs[field]
        for field in ["bodyWeight", "weightGain"]:
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if min_key in kwargs or max_key in kwargs:
                query[field] = {}
                if min_key in kwargs:
                    query[field]["$gte"] = kwargs[min_key]
                if max_key in kwargs:
                    query[field]["$lte"] = kwargs[max_key]
        if kwargs.get("limit"):
            return list(db.bodyweight.find(query).limit(kwargs.get("limit")))
        return list(db.bodyweight.find(query))

    def resolve_diet(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        for field in [
            "day",
            "crudeProteinOfDryMatter",
            "crudeFatContentOfDryMatter",
            "neutralDetergentFiberContentOfDryMatter",
            "organicMatterContentOfDryMatter"
        ]:
            if field in kwargs:
                query[field] = kwargs[field]
        if kwargs.get("min_crudeProteinOfDryMatter") or kwargs.get("max_crudeProteinOfDryMatter"):
            query["crudeProteinOfDryMatter"] = {}
            if kwargs.get("min_crudeProteinOfDryMatter"):
                query["crudeProteinOfDryMatter"]["$gte"] = kwargs["min_crudeProteinOfDryMatter"]
            if kwargs.get("max_crudeProteinOfDryMatter"):
                query["crudeProteinOfDryMatter"]["$lte"] = kwargs["max_crudeProteinOfDryMatter"]
        if kwargs.get("limit"):
            return list(db.diet.find(query).limit(kwargs.get("limit")))
        return list(db.diet.find(query))

    def resolve_gas(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        for field in ["day", "methane", "carbonDioxide", "methaneMeasurementMethod", "durationOfMeasurement"]:
            if field in kwargs:
                query[field] = kwargs[field]
        for field in ["methane", "carbonDioxide"]:
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if min_key in kwargs or max_key in kwargs:
                query[field] = {}
                if kwargs.get(min_key):
                    query[field]["$gte"] = kwargs[min_key]
                if kwargs.get(max_key):
                    query[field]["$lte"] = kwargs[max_key]
        if kwargs.get("limit"):
            return list(db.gas.find(query).limit(kwargs.get("limit")))
        return list(db.gas.find(query))

    def resolve_digestibility(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        for field in ["day", "grossEnergyDigestibility", "dryMatterDigestibility"]:
            if field in kwargs:
                query[field] = kwargs[field]
        for field in ["grossEnergyDigestibility", "dryMatterDigestibility"]:
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if min_key in kwargs or max_key in kwargs:
                query[field] = {}
                if kwargs.get(min_key):
                    query[field]["$gte"] = kwargs[min_key]
                if kwargs.get(max_key):
                    query[field]["$lte"] = kwargs[max_key]
        if kwargs.get("limit"):
            return list(db.digestibility.find(query).limit(kwargs.get("limit")))
        return list(db.digestibility.find(query))

class MilkQuery(ObjectType):
    milk = List(
        MilkType,
        animalIdentifier=Argument(Int, description="Animal ID number"),
        experimentCode=Argument(Int, description="Experiment code"),
        experimentalDesign=Argument(Int, description="Experimental design type"),
        treatmentCode=Argument(Int, description="Treatment group"),
        periodNumber=Argument(Int, description="Period number"),
        day=Argument(Int, description="Exact day"),
        milkProduction=Argument(Float, description="Exact milk production (kg)"),
        milkCrudeProtein=Argument(Float, description="Exact milk crude protein (g/kg)"),
        milkCrudeFat=Argument(Float, description="Exact milk fat (g/kg)"),
        milkLactose=Argument(Float, description="Exact milk lactose (g/kg)"),
        min_day=Argument(Int, description="Minimum day"),
        max_day=Argument(Int, description="Maximum day"),
        min_milkProduction=Argument(Float, description="Minimum milk production"),
        max_milkProduction=Argument(Float, description="Maximum milk production"),
        limit=Argument(Int, description="Limit number of records returned"),
        description="Query milk samples with full filter support"
    )

    def resolve_milk(self, info, **kwargs):
        query = {}

        # Direct match fields
        for field in [
            "animalIdentifier", "experimentCode", "experimentalDesign",
            "treatmentCode", "periodNumber", "day",
            "milkProduction", "milkCrudeProtein", "milkCrudeFat", "milkLactose"
        ]:
            if kwargs.get(field) is not None:
                query[field] = kwargs[field]

        # Range filters
        if kwargs.get("min_day") or kwargs.get("max_day"):
            query["day"] = {}
            if kwargs.get("min_day"):
                query["day"]["$gte"] = kwargs["min_day"]
            if kwargs.get("max_day"):
                query["day"]["$lte"] = kwargs["max_day"]

        if kwargs.get("min_milkProduction") or kwargs.get("max_milkProduction"):
            query["milkProduction"] = {}
            if kwargs.get("min_milkProduction"):
                query["milkProduction"]["$gte"] = kwargs["min_milkProduction"]
            if kwargs.get("max_milkProduction"):
                query["milkProduction"]["$lte"] = kwargs["max_milkProduction"]

        if kwargs.get("limit"):
            return list(db.milk.find(query).limit(kwargs["limit"]))
        return list(db.milk.find(query))
