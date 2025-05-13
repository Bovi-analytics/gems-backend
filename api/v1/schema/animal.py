import graphene
from graphene import ObjectType, Int, String, Float, List, Argument
from api.v1.db import db

# Import related types
# from schema.milk import MilkType
# from schema.intake import IntakeType
from api.v1.schema.bodyweight import BodyWeightType
from api.v1.schema.diet import DietType
from api.v1.schema.gas import GasType
from api.v1.schema.digestibility import DigestibilityType


class AnimalType(ObjectType):
    researchIdentifier = String(description="Name and affiliation of contributor")
    animalIdentifier = Int(description="Animal ID number")
    animalStatus = String(description="Status of the animal: L = Lactating, D = Dry")
    parity = Int(description="Parity of the cow during experiment")
    breed = Int(description="Breed: 1=Holstein, 2=Jersey, etc.")
    daysInMilk = Int(description="Days in milk at start of the experiment")
    cannulation = String(description="Whether cow is cannulated: Yes/No")
    housing = String(description="Type of housing during data collection")

    milk = List(
        # MilkType,
        "api.v1.schema.milk.MilkType",
        day=Argument(Int),
        milkProduction=Argument(Float),
        milkCrudeProtein=Argument(Float),
        milkCrudeFat=Argument(Float),
        milkLactose=Argument(Float),
        min_day=Argument(Int),
        max_day=Argument(Int),
        min_milkProduction=Argument(Float),
        max_milkProduction=Argument(Float),
        limit=Argument(Int),
        description="Milk records with support for both direct and range filtering"
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
        description="Diet data with direct and range filtering"
    )

    intake = List(
        # IntakeType,
        "api.v1.schema.intake.IntakeType",
        day=Argument(Int),
        dryMatterIntake=Argument(Float),
        min_dryMatterIntake=Argument(Float),
        max_dryMatterIntake=Argument(Float),
        limit=Argument(Int),
        description="Intake records with support for both direct and range filtering"
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
        description="Bodyweight records with support for both direct and range filtering"
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
        description="Gas records with support for both direct and range filtering"
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
        description="Digestibility records with support for both direct and range filtering"
    )

    def resolve_milk(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        for field in ["day", "milkProduction", "milkCrudeProtein", "milkCrudeFat", "milkLactose"]:
            if field in kwargs:
                query[field] = kwargs[field]
        for field in ["day", "milkProduction"]:
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if min_key in kwargs or max_key in kwargs:
                query[field] = {}
                if min_key in kwargs:
                    query[field]["$gte"] = kwargs[min_key]
                if max_key in kwargs:
                    query[field]["$lte"] = kwargs[max_key]
        if kwargs.get("limit"):
            return list(db.milk.find(query).limit(kwargs.get("limit")))
        return list(db.milk.find(query))
            

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
        for field in ["crudeProteinOfDryMatter"]:
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if min_key in kwargs or max_key in kwargs:
                query[field] = {}
                if min_key in kwargs:
                    query[field]["$gte"] = kwargs[min_key]
                if max_key in kwargs:
                    query[field]["$lte"] = kwargs[max_key]
        if kwargs.get("limit"):
            return list(db.diet.find(query).limit(kwargs.get("limit")))
        return list(db.diet.find(query))

    def resolve_intake(parent, info, **kwargs):
        query = {"animalIdentifier": parent["animalIdentifier"]}
        for field in ["day", "dryMatterIntake"]:
            if field in kwargs:
                query[field] = kwargs[field]
        for field in ["dryMatterIntake"]:
            min_key = f"min_{field}"
            max_key = f"max_{field}"
            if min_key in kwargs or max_key in kwargs:
                query[field] = {}
                if min_key in kwargs:
                    query[field]["$gte"] = kwargs[min_key]
                if max_key in kwargs:
                    query[field]["$lte"] = kwargs[max_key]
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
                if min_key in kwargs:
                    query[field]["$gte"] = kwargs[min_key]
                if max_key in kwargs:
                    query[field]["$lte"] = kwargs[max_key]
        if kwargs.get("limit"):
            return list(db.gasmeasurement.find(query).limit(kwargs.get("limit")))
        return list(db.gasmeasurement.find(query))

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
                if min_key in kwargs:
                    query[field]["$gte"] = kwargs[min_key]
                if max_key in kwargs:
                    query[field]["$lte"] = kwargs[max_key]
        if kwargs.get("limit"):
            return list(db.digestibility.find(query).limit(kwargs.get("limit")))
        return list(db.digestibility.find(query))

class AnimalQuery(ObjectType):
    animals = List(
        AnimalType,
        parity=Argument(Int, description="Filter cows with exact parity"),
        min_parity=Argument(Int, description="Minimum parity (inclusive)"),
        max_parity=Argument(Int, description="Maximum parity (inclusive)"),
        breed=Argument(Int, description="Filter by specific breed code"),
        breeds=Argument(List(Int), description="Filter by multiple breed codes"),
        animal_status=Argument(String, description="Lactating (L) or Dry (D)"),
        cannulation=Argument(String, description="Yes or No"),
        housing=Argument(String, description="Filter by housing type (e.g. Freestall)"),
        min_days_in_milk=Argument(Int, description="Minimum days in milk"),
        max_days_in_milk=Argument(Int, description="Maximum days in milk"),
        research_identifier=Argument(String, description="Exact match on research identifier"),
        contains_research=Argument(String, description="Search for substring in research identifier"),
        limit=Argument(Int, description="Limit number of animals returned"),
        description="Query to fetch animal data with optional filters"
    )

    def resolve_animals(self, info, **kwargs):
        query = {}

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
        # print(db.animal.find(query))
        if kwargs.get("limit"):
            return list(db.animal.find(query).limit(kwargs.get("limit")))
        return list(db.animal.find(query))
        # return list(db.animals.find(query).limit(kwargs.get("limit", 100)))
