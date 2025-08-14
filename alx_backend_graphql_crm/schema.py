import graphene
# Import the Query and Mutation classes from your crm application's schema.py
# We alias them (e.g., 'as CRMQuery') to avoid naming conflicts if you have other 'Query' classes.
from crm.schema import Query as CRMQuery, Mutation as CRMMutation

# Define the root Query class for your entire GraphQL API.
# It inherits from CRMQuery, bringing in all CRM-specific queries.
# If you had other apps (e.g., 'auth'), you'd inherit from their Query classes here too.
class Query(CRMQuery, graphene.ObjectType):
    """
    The main GraphQL Query class for the entire project,
    aggregating queries from all registered applications.
    """
    pass # No additional fields directly defined here, just combining.

# Define the root Mutation class for your entire GraphQL API.
# It inherits from CRMMutation, bringing in all CRM-specific mutations.
class Mutation(CRMMutation, graphene.ObjectType):
    """
    The main GraphQL Mutation class for the entire project,
    aggregating mutations from all registered applications.
    """
    pass # No additional fields directly defined here, just combining.

# Finally, create the Graphene schema instance.
# This schema object is what will be passed to your GraphQLView in urls.py.
schema = graphene.Schema(query=Query, mutation=Mutation)