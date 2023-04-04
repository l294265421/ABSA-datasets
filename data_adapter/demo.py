from data_adapter.data_object import get_dataset_class_by_name

dataset_name = 'SemEval-2014-Task-4-REST'
dataset = get_dataset_class_by_name(dataset_name)()
print()
