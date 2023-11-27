import os
import glob
import json
import shutil

def _is_file_empty(file_name):
    return os.stat(file_name).st_size == 0

def get_data(file_name) -> list:
    with open(file_name) as f:
        if not _is_file_empty(file_name):
            return json.load(f)
        return {}

def save_data(data, file_name):
    with open(file_name, "w") as f:
        json.dump(data, f, sort_keys=True, indent=2)

def backup(source, destination):
    # Get a list of all backup files
    backups = glob.glob(os.path.join(destination, 'backup*.json'))

    # If there are more than 5 backups
    if len(backups) >= 5:
        # Find the oldest backup file
        indices = [int(file.split('backup')[1].split('.json')[0]) for file in backups]

        # Find the oldest backup file by index
        oldest_backup = 'backup' + str(min(indices)) + '.json'
        oldest_backup = os.path.join(destination, oldest_backup)

        # Delete the oldest backup file
        os.remove(oldest_backup)

    # Create a new backup file
    new_backup = os.path.join(destination, f'backup{len(backups) + 1}.json')

    # Copy the source file to the new backup file
    shutil.copy(source, new_backup)