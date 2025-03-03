import inspect
from typing import List, Dict

class IMG:
    COLLECTION_NAME = "MyImageCollection"

def metadata_decorator(collection: str, actions: List[str]):
    """A decorator to attach metadata to methods."""
    def decorator(func):
        func.__annotations__ = {"metadata": {"collection": collection, "actions": actions}}
        return func
    return decorator

class MyClass:
    @metadata_decorator(collection=IMG.COLLECTION_NAME, actions=["insert", "find"])
    def my_method(self, data: str) -> str:
        """Example method that processes data."""
        return f"Processed: {data}"

    @metadata_decorator(collection="OtherCollection", actions=["update", "delete"])
    def another_method(self):
        """Another annotated method."""
        pass

    def no_annotation_method(self):
        """This method does not have an annotation."""
        pass

def find_annotated_methods(cls):
    """Finds methods in a class that have the 'metadata' annotation and returns their contents."""
    annotated_methods = {}

    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        annotations = getattr(method, "__annotations__", {})
        if "metadata" in annotations:
            annotated_methods[name] = annotations["metadata"]

    return annotated_methods

# Example Usage:
methods_with_metadata = find_annotated_methods(MyClass)

# Print the results
for method, metadata in methods_with_metadata.items():
    print(f"Method: {method}")
    print(f"  Collection: {metadata['collection']}")
    print(f"  Actions: {metadata['actions']}")
    print()
