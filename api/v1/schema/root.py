import graphene
from api.v1.schema.animal import AnimalQuery
from api.v1.schema.milk import MilkQuery
from api.v1.schema.intake import IntakeQuery
from api.v1.schema.bodyweight import BodyWeightQuery
from api.v1.schema.gas import GasQuery
from api.v1.schema.diet import DietQuery
from api.v1.schema.digestibility import DigestibilityQuery



class GemsQuery(
    AnimalQuery, MilkQuery,IntakeQuery, BodyWeightQuery,
    GasQuery, DietQuery, DigestibilityQuery, graphene.ObjectType
    ):
    pass

schema = graphene.Schema(query=GemsQuery)
