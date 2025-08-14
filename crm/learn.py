# project_name/schema.py (or app_name/schema.py)
# This is a common place to define your GraphQL schema.

import graphene # We need to import the graphene library.
from graphql import GraphQLError
from graphene.types.generic import GenericScalar
# GenericScalar is useful for dynamic data like dictionaries


# Graphene is the core Python library for building GraphQL APIs.
                # graphene-django builds on top of this for Django projects,
                # but here we're using its core features directly because we don't have Django models.

# --- Step 1: Define the Output Type for the Data We Will Return ---
# In GraphQL, you must always define the *shape* of the data you expect to get back.
# This is like defining a blueprint for your data objects.

class TaskType(graphene.ObjectType):
    # 'class TaskType(graphene.ObjectType):'
    # This declares a Python class named 'TaskType'.
    # By inheriting from 'graphene.ObjectType', we are telling Graphene that
    # 'TaskType' is a GraphQL "Object Type."
    # An Object Type describes a collection of fields (data points).

    # Now, we define the individual fields (properties) that a Task will have:

    name = graphene.String()
    # 'name = graphene.String()'
    # This defines a field named 'name'.
    # 'graphene.String()' tells Graphene that this field will hold a string value (text).
    # This is the GraphQL equivalent of a string.

    description = graphene.String()
    # 'description = graphene.String()'
    # Another field, also a string, for the task's description.

    status = graphene.String()
    # 'status = graphene.String()'
    # A field to indicate the task's status (e.g., "pending", "completed").

# --- Step 2: Simulate a Data Storage (since we don't have Django models) ---
# In a real application, you'd be interacting with a database (like PostgreSQL, MySQL)
# or an external API. Since we're not using Django models here, we'll create a
# very simple in-memory storage. This means the data will be lost every time
# the server restarts.

class InMemoryDataStore:
    # This class will act as our temporary "database" to store tasks.
    # It's a Python class, but its methods will be 'class methods' which means
    # you call them directly on the class (e.g., InMemoryDataStore.create_task()),
    # rather than creating an instance of the class first.

    _tasks = []
    # '_tasks = []'
    # This is a class variable, a list. It will hold all our task dictionaries.
    # The underscore '_' before 'tasks' is a Python convention indicating it's
    # meant for internal use within this class.
    _projects = []
    _next_project_id = 1

    @classmethod
    # '@classmethod'
    # This is a Python decorator. It means the method below it ('create_task')
    # belongs to the class itself, not to an instance of the class.
    # It receives the class ('cls') as its first argument instead of 'self' (the instance).
    def create_task(cls, name, description, project_id=None):
        # 'cls' refers to the 'InMemoryDataStore' class itself.
        # 'name' and 'description' are the arguments we'll pass when calling this method.

        task = {"name": name, "description": description,
                "status": "pending", "project_id": project_id}
        # This line creates a Python dictionary. Each dictionary represents a single task.
        # We're initializing 'status' to "pending" by default.

        cls._tasks.append(task)
        # 'cls._tasks.append(task)'
        # This adds our newly created 'task' dictionary to the '_tasks' list.

        return task
        # We return the created task dictionary.

    @classmethod
    def create_project(cls, name, description):
        project = {
            "id": cls._next_project_id,
            "name": name,
            "description": description,
            "tasks": []
        }

        cls._projects.append(project)
        cls._next_project_id += 1 #Increment for the next project
        return project

    @classmethod
    def add_task_to_project(cls, project_id, task_data):
        for project in cls._projects:
            if project["id"] == project_id:
                # Create the task and pass its project_id
                task = cls.create_task(task_data["name"], task_data["description"], project_id=project_id)
                project["tasks"].append(task) # Add the task directly to the project's task list
                return project #Return the updated project
        return None


    @classmethod
    def get_all_tasks(cls):
        # This method will retrieve all tasks currently stored in our in-memory list.
        return cls._tasks
        # Returns the entire '_tasks' list.

    @classmethod
    def get_all_projects(cls):
        # When fetching projects, we need to ensure the 'tasks' list for each
        # project actually contains the correct task objects.
        # Our simple in-memory model stores them directly. In a real DB, you'd
        # fetch related objects.
        return cls._projects

# # --- Step A: Define the Project Output Type ---
# We need an ObjectType for our Project, and it will contain a list of TaskType.
class ProjectType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    description = graphene.String()
    tasks = graphene.List(TaskType)





# --- Step 3: Define Your Mutation ---
# A mutation is a type of GraphQL operation that changes data on the server.
# (Queries *fetch* data, Mutations *change* data).

# Redefine CreateTask with validation and more granular output
class CreateTask(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()

    # --- Output Fields for this Mutation ---
    # We're defining a more flexible output now.
    # If successful, it returns a TaskType.
    # If not, it can return 'success: False' and a list of 'errors'.

    Output = TaskType # This means if the mutation *succeeds*, it returns a TaskType object.
                      # We still want this as the primary successful output.

    success = graphene.Boolean()
    # 'success = graphene.Boolean()'
    # A new field: a boolean (True/False) to indicate if the overall mutation was successful.
    # This is a common pattern for mutations to provide clear status.

    errors = graphene.List(graphene.String)
    # 'errors = graphene.List(graphene.String)'
    # A new field: a list of strings to hold error messages if validation fails
    # or other issues occur *without* raising a top-level GraphQL error.
    # This allows for structured error reporting within the mutation's data.

    def mutate(self, info, name, description=None):
        # --- Validation Logic ---
        # This is where you check if the incoming data is valid *before* trying to
        # process it or save it.

        # Validation Method 1: Raise GraphQLError for critical errors
        # This approach stops the mutation immediately and puts an error in the
        # top-level 'errors' array of the GraphQL response. The 'data' for this
        # mutation will be 'null'.
        if len(name) < 3:
            # 'len(name) < 3' checks if the length of the 'name' string is less than 3 characters.
            raise GraphQLError("Task name must be at least 3 characters long.")
            # 'raise GraphQLError(...)': This stops the execution of the 'mutate' method
            # and tells Graphene that an error occurred.
            # Graphene will then format this error into the standard GraphQL error response.

        # Validation Method 2: Return structured errors in the mutation's own output
        # This approach allows the mutation to "succeed" in terms of GraphQL operation
        # (i.e., it returns data in the 'data' field), but that data indicates failure
        # through specific fields like 'success: false' and an 'errors' list.
        # This is useful for user-friendly messages that don't halt the entire operation
        # and provide more specific context about *why* it failed within the result data.
        if "bad_word" in name.lower():
            # 'name.lower()' converts the name to lowercase for case-insensitive checking.
            # '"bad_word" in ...' checks if the substring "bad_word" is present.
            return CreateTask(success=False, errors=["Task name contains a forbidden word."])
            # If this condition is met, we return an instance of 'CreateTask' (our mutation).
            # We explicitly set 'success=False' and populate the 'errors' list.
            # Notice we don't return 'name', 'description', or 'status' here, as the task wasn't created.
            # GraphQL will return 'null' for those fields if they are requested by the client
            # but not provided in the return statement when 'success' is false.

        # --- If all validations pass, proceed with business logic ---
        task = InMemoryDataStore.create_task(name, description)
        # Create the task using our in-memory store.

        # --- Return success and the created task ---
        return CreateTask(
            name=task["name"],
            description=task["description"],
            status=task["status"],
            success=True, # Explicitly indicate success
            errors=[]     # Explicitly provide an empty error list
        )


# --- Step A: Define an Input Type for a Single Item in the Bulk List ---
# When you pass a list of complex objects as input, you define an InputObjectType.
# This is similar to ObjectType but specifically for input arguments.
class TaskInput(graphene.InputObjectType):
    # 'class TaskInput(graphene.InputObjectType):'
    # This class defines the structure for *each individual task* that will be part
    # of the bulk creation list. It's like a mini-blueprint for the items in the input list.
    name = graphene.String(required=True)
    description = graphene.String()

# --- Step B: Define the BulkCreateTasks Mutation ---

class BulkCreateTask(graphene.Mutation):
    class Arguments:
        # 'tasks_data' will be a list of 'TaskInput' objects.
        tasks_data = graphene.List(TaskInput, required=True)
        # 'graphene.List(TaskInput, required=True)'
        # This specifies that the argument 'tasks_data' must be a list,
        # and each item in that list must conform to the 'TaskInput' structure.
        # 'required=True' means the client must provide this list (even if it's empty).

    # --- Output Fields for Bulk Creation ---
    # The output will summarize the results of the batch.
    created_tasks = graphene.List(TaskType)
    # 'created_tasks = graphene.List(TaskType)'
    # This field will return a list of all the tasks that were successfully created.

    success_count = graphene.Int()
    # 'success_count = graphene.Int()'
    # An integer showing how many tasks were successfully created.

    errors = graphene.List(GenericScalar)
    # 'errors = graphene.List(GenericScalar)'
    # A list to store errors for individual items in the batch.
    # 'GenericScalar' is a flexible Graphene type that can hold any JSON-like data
    # (dictionaries, lists, strings, numbers). We use it here because our error
    # objects will be dictionaries (e.g., {"name": "X", "error": "Too short"}).

    def mutate(self, info, tasks_data):
        # 'tasks_data' will be the list of 'TaskInput' objects sent by the client.
        created_tasks_list = []

        errors_list = []

        success_count = 0

        for task_input in tasks_data:
            # We loop through each individual 'task_input' object in the 'tasks_data' list.
            # Each 'task_input' will be an instance of 'TaskInput' with 'name' and 'description' properties.
            name = task_input.name
            description = task_input.description

            # --- Validation for Each Item in the Batch ---
            # We apply validation rules to each task individually.
            # If an item fails, we add an error and 'continue' to the next item,
            # allowing the rest of the batch to proceed.


            if len(name) < 3:
                errors_list.append({"name": name, "error": "Task name must be at least 3 characters long."})
                continue # Skip the rest of the loop for this item and move to the next.

            if "forbidden" in name.lower():
                errors_list.append({"name": name, "error": "Task name contains a forbidden word."})
                continue  # Skip this item.

            # --- If validation passes for this item ---
            task = InMemoryDataStore.create_task(name, description)

            created_tasks_list.append(task)
            # Add the newly created task to our list of successful tasks.

            success_count += 1
            # Increment the success counter

        return BulkCreateTask(
            created_tasks = created_tasks_list,
            success_count=success_count,
            errors=errors_list
        )

# --- Step C: Define the CreateProjectWithTasks Mutation ---

class CreateProjectWithTasks(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()
        # The key to nested creation: a list of `TaskInput` objects.
        tasks = graphene.List(TaskInput)
        # 'tasks = graphene.List(TaskInput)'
        # This argument allows the client to send a list of task inputs
        # that will be created and associated with the new project.

    Output = ProjectType # The output of this mutation will be a ProjectType object.

    def mutate(self, info, name, description=None, tasks=None):
        # 'tasks=None' because the list of nested tasks is optional.

        # 1. Create the parent object (Project) first.
        project = InMemoryDataStore.create_project(name, description)
        # 'project' now holds a dictionary representing the newly created project.

        # 2. If nested tasks are provided, iterate and create them.
        if tasks: # Checks if the 'tasks' list was provided and is not empty.
            for task_data in tasks:
                # 'task_data' is an instance of 'TaskInput' (e.g., {'name': '...', 'description': '...'}).

                # In a real application, you might add validation for each nested task here.
                # For simplicity, we'll skip detailed validation within the nested loop for this example,
                # assuming the individual TaskInput would pass basic checks or be handled by the called method.

                InMemoryDataStore.add_task_to_project(project["id"], task_data)
                # We call our data store method to create the task and link it to the project
                # using the project's ID.

        # 3. Return the newly created project, including its nested tasks.
        # We need to ensure the returned project object correctly reflects the tasks added.
        # In our simple InMemoryDataStore, the 'project' dictionary already has its 'tasks' list updated.
        # If you were fetching from a real DB, you might re-fetch the project to include its relations.

        # For our InMemoryDataStore, the 'project' object obtained from create_project
        # and subsequently modified by add_task_to_project holds the complete data.
        # We just need to ensure we return it correctly formatted.

        return CreateProjectWithTasks(
            id=project["id"],
            name=project["name"],
            description=project["description"],
            tasks=project["tasks"] # This list will contain the newly created task dictionaries.
        )


# --- Step C: Register the New Mutation ---

# --- Step 4: Assemble Your Root Mutation and Query Classes ---
# In GraphQL, you have a "root" Query type and a "root" Mutation type.
# These are the entry points for all your available queries and mutations.

class Mutation(graphene.ObjectType):
    # 'class Mutation(graphene.ObjectType):'
    # This defines our main GraphQL Mutation type. All individual mutations
    # (like CreateTask) need to be registered here.

    create_task = CreateTask.Field()
    # 'create_task = CreateTask.Field()'
    # This line exposes our 'CreateTask' mutation.
    # 'CreateTask.Field()' is a special Graphene helper that makes the mutation
    # available as a field under the 'Mutation' type.
    # The name 'create_task' here will be the name clients use in their GraphQL queries.

    bulk_create_task = BulkCreateTask.Field()
    create_project_with_tasks = CreateProjectWithTasks.Field()


# --- Step 5: (Optional but Recommended) Add a Query to See the Data ---
# To confirm our mutation works, it's helpful to have a query that can fetch
# all the tasks we've created.

class Query(graphene.ObjectType):
    # 'class Query(graphene.ObjectType):'
    # This defines our main GraphQL Query type, which serves as the entry point
    # for all read operations.

    all_tasks = graphene.List(TaskType)
    # 'all_tasks = graphene.List(TaskType)'
    # This defines a query field named 'all_tasks'.
    # 'graphene.List(TaskType)' means this field will return a *list* of objects,
    # and each object in the list will conform to our 'TaskType' blueprint.

    all_projects = graphene.List(ProjectType)  # New query to fetch all projects


    def resolve_all_tasks(self, info):
        # 'def resolve_all_tasks(self, info):'
        # This is the "resolver" method for the 'all_tasks' query.
        # Graphene calls this method when a client requests the 'all_tasks' field.
        # 'self' refers to the 'Query' instance.
        # 'info' is the same context object as in mutations.

        return InMemoryDataStore.get_all_tasks()
        # We call our simulated data store to get all the tasks.
        # The list of task dictionaries returned by this method will be automatically
        # converted by Graphene into the 'TaskType' format for the GraphQL response.

    def resolve_all_projects(self, info):
        return InMemoryDataStore.get_all_projects()


# --- Step 6: Create the GraphQL Schema ---
# The schema is the central definition of your GraphQL API. It combines your
# Query and Mutation types into a single, runnable structure.

schema = graphene.Schema(query=Query, mutation=Mutation)
# 'schema = graphene.Schema(query=Query, mutation=Mutation)'
# This line creates the final GraphQL schema object.
# 'query=Query': We specify that our 'Query' class is the root query type.
# 'mutation=Mutation': We specify that our 'Mutation' class is the root mutation type.
# This 'schema' object is what you would typically pass to your Django GraphQL view
# (e.g., in your `urls.py` where you configure `GraphQLView`).