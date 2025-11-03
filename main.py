import argparse
import json
import logging
import sys

from task import Task, load_task

tasks, archives = [], []
storage_file = "tasks.json"
archived_file = "archived.json"

# todo: write a simple task management app.

# USAGE: python main.py <add,list,update,remove,clear>

### MAIN ###

def main():
    parser = argparse.ArgumentParser(description="A command line task tracker.")

    parser.add_argument("action", help="The action to take (e.g. add, update, list, remove etc.)")

    parser.add_argument("--debug", help="Toggle debug output", action="store_true")

    # update-specific args
    parser.add_argument("id", nargs="?", help="Select item by id")
    parser.add_argument("-s", "--status", choices=["in_progress", "done"], help="Update item status")
    parser.add_argument("-t", "--title", help="Update title of an item")
    parser.add_argument("-d", "--desc", help="Update description of an item")
    parser.add_argument("-k", "--keyword", help="Keyword used to filter items")
    parser.add_argument("-u", "--user", help="Update user assigned to an item")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

        logging.debug("DEBUG MODE ACTIVE")
        logging.debug("Print command line arguments")
        argsdict = vars(args)
        logging.debug(argsdict)

    # print out debug output


    match args.action:
        case "help":
            parser.print_help()
        case "add":
            logging.debug("Adding Item")
            read_tasks(storage_file)
            add_task()
            write_tasks(storage_file)
        case "update":
            logging.debug("Updating Item")
            if not args.id: 
                print("Must provide a ID for item to update.")
                sys.exit()
            read_tasks(storage_file)
            task = next((t for t in tasks if t.id == args.id), None)
            if not task:
                print(f"No item found with ID {args.id}")
            else:
                if args.status:
                    update_task_status(task, args.status)
                    print(f"Updated item status for item ID {task.id}.")
                if args.title or args.desc or args.user:
                    update_task(task, args.title, args.desc, args.user)
                    print(f"Modified item for item ID {task.id}.")
                write_tasks(storage_file)
        case "list":
            logging.debug("Listing Items")
            read_tasks(storage_file)
            if not tasks:
                print("No Item found.")
            else:
                print("Current Items:")
                for task in tasks:
                    print(f"Title: {task.title}")
                    print(f"Description: {task.description}")
                    print(f"User: {task.user}")
                    print(f"Status: {task.status}")
        case "remove":
            logging.debug("Removing Item")
            if not args.id:
                print("Must provide an ID for item to remove.")
                sys.exit()
            read_tasks(storage_file)
            #Check if item with that ID exists
            task = next((t for t in tasks if t.id == args.id), None)
            if not task:
                print(f"No item found with ID {args.id}")
            else:
                remove_task(args.id)
                write_tasks(storage_file)
                print(f"Removed item with ID {args.id}")

        case "search":
            logging.debug("Searching Items")
            if not args.keyword:
                print("Please provide a keyword using -k or --keyword.")
                sys.exit()
            read_tasks(storage_file)
            matched = [t for t in tasks if args.keyword.lower() in t.title.lower() or args.keyword.lower() in t.description.lower()]
            if not matched:
                print(f"No tasks found matching keyword: {args.keyword}")
            else:
                print(f"Tasks matching '{args.keyword}':")
                for task in matched:
                    print(f"Title: {task.title}")
                    print(f"Status: {task.status}")

        case "archives":
            logging.debug("Archiving Items")
            read_archived(archived_file)
            show_archives()
            write_archived(archived_file)
        case "clear":
            logging.debug("Clearing All Items")
            read_tasks(storage_file)
            answer = input("This will delete ALL tasks. Are you sure? (Y/N): ")
            if answer.lower() not in ("y", "yes"):
                print("Aborted.")
                sys.exit()
            clear_all_tasks()
            write_tasks(storage_file)
            print("All tasks cleared.")
        case _:
            print("Unidentified command. Options are add, update, list, remove, and help.")
            parser.print_help()

    # Exit program


### COMMANDS ###

# Add task
def add_task():
    print("Creating Task from User Input")
    title = input("Please enter a title: ")
    description = input("Please enter a short description: ")
    user = input("Please enter a user (or leave blank to skip): ")
    tasks.append(Task(title, description, user))

# Update item status
def update_task_status(task, new_status):
    task.status = new_status

# Update item content
def update_task(task, new_title, new_desc, new_user):
    if new_title:
        task.title = new_title
    if new_desc:
        task.description = new_desc
    if new_user:
        task.user = new_user

# Remove item
def remove_task(task_id):
    global tasks
    for task in tasks:
        if task.id == task_id:
            task_to_archive = task
    tasks = [t for t in tasks if t.id != task_id]
    
    # archived task
    archives.append(task_to_archive)
    read_archived(archived_file)
    write_archived(archived_file)

# Item Search
def search_tasks(keyword):
    matched_tasks = []

    for task in tasks:
        title_match = keyword.lower() in task.title.lower()
        desc_match = keyword.lower() in task.description.lower()

        if title_match or desc_match:
            matched_tasks.append(task)

    return matched_tasks

#Clear all tasks
def clear_all_tasks():
    global tasks
    tasks = []
    
# Show archives
def show_archives():
    print("Archived tasks: ")
    for task in archives:
        print(task.to_dict())
        

### File Handling ###

# Write to JSON file
def write_tasks(filename):
    logging.debug("Writing tasks to file " + filename)
    with open(filename, "w") as file:
        json_str = json.dumps([t.to_dict() for t in tasks])
        file.write(json_str)
    logging.debug("Tasks written to file " + filename)

def write_archived(filename):
    logging.debug("Writing archived tasks to file " + filename)
    with open(filename, "w") as file:
        json_str = json.dumps([t.to_dict() for t in archives])
        file.write(json_str)
    logging.debug("Tasks written to archived file " + filename)

# Read from JSON file
def read_tasks(filename):
    logging.debug("Reading tasks from file " + filename)
    try:
        with open(filename, "r") as file:
            json_tasks = json.loads(file.read())
        print(json_tasks)
        for task in json_tasks:
            tasks.append(load_task(task))

    except json.JSONDecodeError:
        logging.debug("File named " + filename + " is empty.")
        pass
    except FileNotFoundError:
        print("No file named " + filename + " found.")
        resp = input("Would you like the file to be created? (y/N): ")
        if resp.lower() == "y" or resp.lower() == "yes":
            logging.debug("File will be created at " + filename)
        else:
            print("No file named " + filename + " found. Exiting.")
            sys.exit()
    logging.debug("Read complete.")

def read_archived(filename):
    logging.debug("Reading archived tasks from file " + filename)
    try:
        with open(filename, "r") as file:
            json_tasks = json.loads(file.read())
            for task in json_tasks:
                archives.append(load_task(task))
    except json.JSONDecodeError:
        logging.debug("File named " + filename + " is empty.")
        pass
    except FileNotFoundError:
        print("No file named " + filename + " found.")
        print(f"Creating a file name {filename} for archived items.")

if __name__ == "__main__":
    main()