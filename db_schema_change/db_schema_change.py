import os
import random
import shutil
import ruamel.yaml

yaml = ruamel.yaml.YAML()

def generate_new_entity_id(old_id):
    return ''.join(random.sample(old_id, len(old_id)))

def log_change(log_file, file_path, original, updated):
    with open(log_file, 'a') as log:
        log.write(f"In file {file_path}: '{original}' replaced with '{updated}'\n")

# Update entity_id, database, and schema names
def update_entity_ids_and_db_schema(data, entity_id_map, old_db, old_schema, new_db, new_schema, file_path, log_file):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                for old_id, new_id in entity_id_map.items():
                    if old_id in value:
                        original_value = value
                        updated_value = value.replace(old_id, new_id)
                        data[key] = updated_value
                        log_change(log_file, file_path, original_value, updated_value)
                if old_db in value or old_schema in value:
                    original_value = value
                    updated_value = value.replace(old_db, new_db).replace(old_schema, new_schema)
                    if original_value != updated_value:
                        data[key] = updated_value
                        log_change(log_file, file_path, original_value, updated_value)
            else:
                update_entity_ids_and_db_schema(value, entity_id_map, old_db, old_schema, new_db, new_schema, file_path, log_file)

    elif isinstance(data, list):
        for i in range(len(data)):
            if isinstance(data[i], str):
                original_value = data[i]
                updated_value = original_value.replace(old_db, new_db).replace(old_schema, new_schema)
                if original_value != updated_value:
                    data[i] = updated_value
                    log_change(log_file, file_path, original_value, updated_value)
            else:
                update_entity_ids_and_db_schema(data[i], entity_id_map, old_db, old_schema, new_db, new_schema, file_path, log_file)

    return data

# Process YAML files
def process_yaml_file(file_path, entity_id_map, old_db, old_schema, new_db, new_schema, log_file):
    with open(file_path, 'r') as file:
        try:
            data = yaml.load(file)
        except ruamel.yaml.YAMLError as exc:
            print(f"Error processing file {file_path}: {exc}")
            return

    updated_data = update_entity_ids_and_db_schema(data, entity_id_map, old_db, old_schema, new_db, new_schema, file_path, log_file)

    with open(file_path, 'w') as file:
        yaml.dump(updated_data, file)

    original_entity_id = os.path.splitext(os.path.basename(file_path))[0]
    new_entity_id = updated_data.get('entity_id', original_entity_id)
    if original_entity_id != new_entity_id:
        new_file_name = file_path.replace(original_entity_id, new_entity_id)
        
        new_dir = os.path.dirname(new_file_name)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        
        print(f'Renaming file {file_path} to {new_file_name}')
        shutil.move(file_path, new_file_name)
        log_change(log_file, file_path, original_entity_id, new_entity_id)

def create_entity_id_map(folder_path):
    entity_id_map = {}
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    try:
                        data = yaml.load(f)
                        collect_entity_ids(data, entity_id_map)
                    except ruamel.yaml.YAMLError as exc:
                        print(f"Error reading file {file_path}: {exc}")

    for old_id in entity_id_map.keys():
        entity_id_map[old_id] = generate_new_entity_id(old_id)
    
    return entity_id_map

def collect_entity_ids(data, entity_id_map):
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() == "entity_id" and value not in entity_id_map:
                entity_id_map[value] = None
            else:
                collect_entity_ids(value, entity_id_map)
    elif isinstance(data, list):
        for item in data:
            collect_entity_ids(item, entity_id_map)

def rename_folder_structure(output_folder_path, old_db, old_schema, new_db, new_schema):
    databases_folder_path = os.path.join(output_folder_path, "databases")
    for root, dirs, files in os.walk(databases_folder_path, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            new_name = name.replace(old_db, new_db).replace(old_schema, new_schema)
            new_dir_path = os.path.join(root, new_name)
            if dir_path != new_dir_path:
                print(f'Renaming directory {dir_path} to {new_dir_path}')
                shutil.move(dir_path, new_dir_path)

def copy_directory_structure(input_folder_path, output_folder_path):
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)
    shutil.copytree(input_folder_path, output_folder_path, dirs_exist_ok=True)

# Copy all files and directories to output and handle renaming
def process_folder_with_entity_ids_and_db_schema(input_folder_path, output_folder_path, old_db, old_schema, new_db, new_schema):
    
    copy_directory_structure(input_folder_path, output_folder_path)

    log_file = os.path.join(output_folder_path, 'log.txt')
    if os.path.exists(log_file):
        os.remove(log_file)  

    entity_id_map = create_entity_id_map(output_folder_path)
    
    for root, _, files in os.walk(output_folder_path):
        for file in files:
            if file.endswith('.yaml') or file.endswith('.yml'):
                file_path = os.path.join(root, file)
                print(f'Processing file: {file_path}')
                process_yaml_file(file_path, entity_id_map, old_db, old_schema, new_db, new_schema, log_file)

    rename_folder_structure(output_folder_path, old_db, old_schema, new_db, new_schema)


def main():
    input_folder_path = "/path_to_original_serialized_folder"
    output_folder_path = "/desired_path_of_modified_serialized_folder"

    old_db = input("Enter the old database name: ")
    old_schema = input("Enter the old schema name: ")
    new_db = input("Enter the new database name: ")
    new_schema = input("Enter the new schema name: ")

    process_folder_with_entity_ids_and_db_schema(input_folder_path, output_folder_path, old_db, old_schema, new_db, new_schema)
    print("All files have been copied, folder structure updated, and YAML files have been processed in the converted folder.")
    print(f"Changes have been logged in {output_folder_path}/log.txt")

if __name__ == "__main__":
    main()
