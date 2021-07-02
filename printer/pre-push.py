import sys, os, re, time
from datetime import datetime

"""
A global dictionary of constants
"""
CONSTANTS = {
    "ISO_FORMAT_REGEX"       : r'\d+-\d+-\d+\s+\d+:\d+:\d+', # e.g. '2019-12-20 6:56:00'
    "EDGEZONERP_BUILD_CMD"   : "ls -al", # "dotnet restore build.proj | dotnet build build.proj",
    "PY_DATETIME_FORMAT"     : "%Y-%m-%d %H:%M:%S", # e.g. '2019-12-20 6:56:00'
    "DELETE_PUSH_HASH_VALUE" : "0000000000000000000000000000000000000000",
    "ROOT_DIRECTORIES"       : ["test"], # ["Controllers", "Attributes"],
    "DEPENDENCY_REGEX"       : r'EdgeZoneRP.*;',
    "BASE_NAMESPACE_PATH"    : "src\\EdgeZoneRP",
    "DELETE_PUSH_REF_VALUE"  : "(delete)",
    "EDGEZONERP"             : "EdgeZoneRP",
    "SWAGGER_FILE_NAME"      : "swagger",
    "ROOT_DIR_DELIM"         : "."
}


"""
Function simply formats date in ISO format
and converts into a datetime object ...
1. Formatting using regex from ISO git datetime repr
2. Create a datetime object and returns that ...
param: unformatted date (str in git ISO datetime)
return: python datetime object
"""
def get_formatted_datetime(unformatted_date):
    if not unformatted_date: # None or empty
        return None

    # attempt to format and return proper date: e.g. 
    regex =  CONSTANTS["ISO_FORMAT_REGEX"] # e.g. '2019-12-20 6:56:00'
    formatted_date_arr = re.findall(regex, unformatted_date)
    if len(formatted_date_arr) == 0:
        return None

    # finally convert to proper datetime object and ret
    formatted = formatted_date_arr[0]
    datetime_format = CONSTANTS["PY_DATETIME_FORMAT"]
    datetime_object = datetime.strptime(formatted, datetime_format)
    return datetime_object


"""
Function returns the most recent global
push date on the current branch. It scans the
output of git reflog to attempt to find this
return: date (python datetime object)
"""
def get_most_recent_push_datetime():
    search_str = "findstr checkout" if "win" in sys.platform else "grep checkout"
    push_date_stream = os.popen(f'git reflog --date=iso | {search_str}')
    push_date_str = push_date_stream.readline() # gets most recent push from log
    # returns format '2019-12-20 6:56:00'
    most_recent_global_push_date = get_formatted_datetime(push_date_str) 
    return most_recent_global_push_date


"""
Function returns the most recently modified time
of the *\EdgeZoneRP\src\Docs\api\swagger file
A. The swagger spec file gets rebuilt(?) when there are 
changes to the API specification/definitions hence
we use the last-modified date for the file as a check
on when it was last built...
B. We then use the most_recent commit together with the
most_recent push information to get a sense of changes
to the implementation of the API action methods
Assumption: Each new build may update this file
param: swagger_file_path (str)
"""
def get_swagger_modified_datetime(swagger_file_path):
    if not swagger_file_path:
        return None
    modified_date = os.path.getmtime(swagger_file_path)
    datetime_struct = time.strptime(time.ctime(modified_date))
    most_recent_modification_datetime = datetime.fromtimestamp(time.mktime(datetime_struct))
    return most_recent_modification_datetime


"""
Function explores all files in this dir
to see if any of these files need to be modified
param: dir_path (str)
param: files_to_be_pushed (set of files to be pushed)
return: boolean
"""
def is_dir_and_dependencies_to_be_pushed(dir_path, files_to_be_pushed):
    # loop through all the items in the dir_path
    for entry in os.listdir(dir_path):
        entry_path = f'{dir_path}\\{entry}' # could be a file/dir
        if not os.path.islink(entry_path) and not entry.startswith("."):
            result = False
            if os.path.isdir(entry_path):
                result = is_dir_and_dependencies_to_be_pushed(entry_path, files_to_be_pushed)
            elif os.path.isfile(entry_path):
                result = is_file_and_dependencies_to_be_pushed(entry, entry_path, files_to_be_pushed)
            if result:
                return result
    return False


"""
Function explores all files in this dir
to see if any of these files need to be modified
param: filename (str)
param: file_path (str)
param: files_to_be_pushed (set of files to be pushed)
return: boolean
"""
def is_file_and_dependencies_to_be_pushed(filename, file_path, files_to_be_pushed):
    # check to see if file is in files_to_be_pushed
    if filename in files_to_be_pushed:
        return True
    # return result from exploring file dependencies
    return explore_dependencies(file_path, files_to_be_pushed)


"""
Loops through selected repositories
----- API related directories -----
to query if any changes occurred since
last push and then enforces a build before
pushing up to ADO
@param: root_dirs [list of primary paths]
"""
def check_for_api_committed_changes(root_dirs,
                                    swagger_most_recent_mod, 
                                    global_most_recent_push,
                                    files_to_be_pushed):
    # validate input first...
    if not root_dirs: # null or empty
        return False # means no changes committed
    
    # boolean to keep track of whether we should rebuild project
    rebuild = False
    files_to_be_pushed_not_empty = len(files_to_be_pushed) == 0

    # loop through relevant dirs and sub-dirs to check
    for root_dir in root_dirs:
        # check every sub-dir ...
        for entry in os.listdir(root_dir):
            entry_path = f'{root_dir}\\{entry}' # could be a file/dir
            # print(entry_path)
            # get the most recent commit date
            commit_date_stream = os.popen(f'git log -n 1 --date=iso --pretty=format:%cd {entry_path}')
            commit_date = commit_date_stream.readline().strip()
            # print(commit_date)
            if not commit_date:
                continue

            # otherwise implement logic defined in function comments
            most_recent_commit_dt = get_formatted_datetime(commit_date)
            if not most_recent_commit_dt:
                continue

            # API definition changes check ... 
            if swagger_most_recent_mod and most_recent_commit_dt > swagger_most_recent_mod:
                # print("swagger_most_recent_mod")
                rebuild = True
                break
            
            # condition == True means unpushed commits exist, rebuild project
            # This is more focussed on API implementation changes within repo
            if global_most_recent_push:
                if most_recent_commit_dt > global_most_recent_push:
                    # print("global_most_recent_push")
                    rebuild = True
                    break
            else:
                # check the collection of files to be pushed and check if curr file
                # is part of this list ... also we explore sub-dependencies as well
                if files_to_be_pushed_not_empty and not os.path.islink(entry_path):
                    if os.path.isdir(entry_path):
                        if is_dir_and_dependencies_to_be_pushed(entry_path, files_to_be_pushed):
                            # print("is_dir_and_dependencies_to_be_pushed")
                            rebuild = True
                            break
                    elif os.path.isfile(entry_path):
                        if is_file_and_dependencies_to_be_pushed(entry, entry_path, files_to_be_pushed):
                            # print("is_file_and_dependencies_to_be_pushed")
                            rebuild = True
                            break
        # if rebuild flag set then exit
        if rebuild:
            break
    # return the rebuild flag/boolean
    return rebuild


"""
Function reads the content of the file for the
include lines: using .* and then parses it for
the section indicating the dependencies ...
param: file_path (str)
param: files_to_be_pushed (set of files to pushed)
return: boolean
"""
def explore_dependencies(file_path, files_to_be_pushed):
    if "win" in sys.platform:
        search_str = f'type {file_path} | findstr using'
    else:
        search_str = f'cat {file_path} | grep using'
    file_content_stream = os.popen(search_str)
    searched_file_content_arr = file_content_stream.readlines()
    if len(searched_file_content_arr) == 0:
        return False # means no rebuild necessary

    # otherwise extract the dependencies from the file...
    filtered_list = list(filter(lambda entry: CONSTANTS["EDGEZONERP"] in entry, searched_file_content_arr))
    # print("filtered_list in explore_dependencies: ", filtered_list)

    # get the extension after "EdgeZoneRP" and build new paths for them...
    entries = get_full_path_for_extensions(CONSTANTS["EXTENSIONS_BASE_DIR"], filtered_list)
    # print("entries in explore_dependencies: ", entries)

    # loop through the list and for each entry call appropraite function
    for entry_path in entries:
        if os.path.isdir(entry_path):
            if is_dir_and_dependencies_to_be_pushed(entry_path, files_to_be_pushed):
                return True
        elif os.path.isfile(entry_path):
            entry = entry_path.split("\\")[-1] # extract the file/dir name
            if is_file_and_dependencies_to_be_pushed(entry, entry_path, files_to_be_pushed):
                return True
    return False

                                 
"""
Takes in list: e.g. "using .*.EdgeZoneRP.*;"
Filters this list and constructs a full path
to the dependency directories to perform full
search ... 
param: base_path (str)
param: filtered_list (arr)
return: entries (list of dirs and files dependencies)
"""
def get_full_path_for_extensions(base_path, filtered_list):
    entries = []
    for entry in filtered_list:
        res = re.findall(CONSTANTS["DEPENDENCY_REGEX"], entry.strip())
        if len(res) == 0:
            continue
        trimmed = res[0][len(CONSTANTS["EDGEZONERP"]):-1] # with sep='.'
        trimmed_mod_sep = trimmed.replace('.', "\\")
        # build the full path ... and add to list ...
        full_path = base_path + trimmed_mod_sep
        entries.append(full_path)
    # return the final list ...
    return entries


"""
Function searches for the full_path of the
swagger file... Could just hardcode this but
what's the fun in it haha
"""
def get_swagger_file_path():
    base_dir = os.getcwd()
    splitted_substrs = base_dir.split("\\.")
    if len(splitted_substrs) == 0:
        return None
    search_base_dir = splitted_substrs[0]
    return search_for_swagger_file_path(search_base_dir)


"""
Function searches for swagger spec file
from search_base_dir recursively ... Search
only hardlinks [symlinks are ignored]
param: search_base_dir
return: swagger_file_path (str)
"""
def search_for_swagger_file_path(search_base_dir):
    # search for the swagger file fullpath...
    for entry in os.listdir(search_base_dir):
        full_path = f'{search_base_dir}\\{entry}'
        # print("swagger: " + full_path)
        condition_1 = entry == CONSTANTS["SWAGGER_FILE_NAME"]
        condition_2 = os.path.isfile(full_path)
        condition_3 = not entry.startswith(".")
        condition_4 = not os.path.islink(full_path)
        condition_5 = os.path.isdir(full_path)
        if condition_1 and condition_2:
            return full_path
        if condition_3 and condition_4 and condition_5:
            result = search_for_swagger_file_path(full_path)
            if result:
                return result
    return None


"""
Function builds the roots directory paths
we want to begin searching for updates to 
API changes ... uses os.getcwd() etc...
return root_dirs (array) None == abort
"""
def get_root_directories():
    base_dir = os.getcwd()
    splitted_substrs = base_dir.split("\\.")
    if len(splitted_substrs) == 0:
        return None
    # print(splitted_substrs[0])
    # extract the actual base dir and reconstruct paths
    # to the relevant classes: Attributes class/dir and 
    # Controllers class/dir ...
    root_dirs = []
    search_base_dir = splitted_substrs[0]

    # assumes that there exist a single unique folder by those names
    # across the entire repository ....
    dirs_to_found = len(CONSTANTS["ROOT_DIRECTORIES"])
    search_for_root_directories(search_base_dir, root_dirs, dirs_to_found)
    if len(root_dirs) == 0:
        return None
    return root_dirs


"""
Function searches for root directories
from base_dir recursively ... We search
only hardlinks [symlinks are ignored]
param: base_dir
param: root_dirs (list of relevant directories)
param: dirs_to_found (num dirs to find)
return: root_dirs (list)
"""
def search_for_root_directories(base_dir, root_dirs, dirs_to_found):
    if dirs_to_found != 0:
        for entry in os.listdir(base_dir):
            full_path = f'{base_dir}\\{entry}'
            # print(full_path)
            condition_1 = not entry.startswith(".")
            condition_2 = not os.path.islink(full_path)
            condition_3 = os.path.isdir(full_path)
            if condition_1 and condition_2 and condition_3:
                if entry in CONSTANTS["ROOT_DIRECTORIES"]:
                    root_dirs.append(full_path)
                    dirs_to_found -= 1
                    # perform look-ahead to exit early...
                    if dirs_to_found == 0:
                        break
                # continue searching for the relevant directories
                search_for_root_directories(full_path, root_dirs, dirs_to_found)
                # perform a look-ahead to exit early ...
                if len(root_dirs) == len(CONSTANTS["ROOT_DIRECTORIES"]):
                    break


"""
Function formats unformatted remote_branch
path to extract the remote branch name 
e.g. refs/heads/master -> master

"""
def extract_remote_branch_name(remote_branch_unformatted):
    remote_branch_unformatted = remote_branch_unformatted.strip()
    splitted = remote_branch_unformatted.split("/")
    if len(splitted) != 3: # expected at least [refs/head/***remote_name***]
        return None
    return splitted[2]


"""
Function returns the files git push
will be modifying ...
return: (set) of files to be pushed
"""
def get_files_to_be_pushed():
    _, remote_repo, _, _, _, remote_branch_unformatted, _ = sys.argv
    remote_branch = extract_remote_branch_name(remote_branch_unformatted)
    full_diff_param = f'{remote_repo}/{remote_branch}'
    # build the command for getting the modified files to be pushed
    command = f'git diff --name-only --cached {full_diff_param}'
    return_stream = os.popen(command)
    return_list = return_stream.readlines()
    # create the new set to return ...
    formatted_return_set = set()
    for return_item in return_list:
        return_splitted = return_item.strip().split("/")
        if return_splitted:
            formatted_return_set.add(return_splitted[-1])
    return formatted_return_set
    

"""
Function returns the path to the 
base directory ... hardcoded here
as: .*\src\EdgeZoneRP\.*
CHECK RETURN VALUE WHEN len(splitted_substrs) == 0
return: base directory path for repo (str)
"""
def save_extensions_base_directory_path():
    base_dir = os.getcwd()
    splitted_substrs = base_dir.split("\\.")
    if len(splitted_substrs) == 0:
        CONSTANTS["EXTENSIONS_BASE_DIR"] = base_dir # save non-null string [singular point of failure?]
    search_base_dir = splitted_substrs[0]
    CONSTANTS["REPO_BASE_DIR"] = search_base_dir
    # save this to the global constants file...
    fullpath = f'{search_base_dir}\\{CONSTANTS["BASE_NAMESPACE_PATH"]}'
    CONSTANTS["EXTENSIONS_BASE_DIR"] = fullpath


"""
Function initiates rebuild by running
command: dotnet build build.proj
"""
def handle_push(rebuild):
    if rebuild:
        print("Project needs to be rebuilt to validate API changes")
        print("Rebuild initiated ...")
        # change directory into the base directory
        os.system(f'cd {CONSTANTS["REPO_BASE_DIR"]}')
        # run the build command from the new path ...
        result = os.system(f'{CONSTANTS["EDGEZONERP_BUILD_CMD"]}')
        if result == 0:
            print("Rebuild successful :)")
        else:
            print("Attempt to rebuild project failed :(")
    else:
        print("Rebuild not necessary :)")

"""
sys.argv[0] == this script's name... params start from index 1
sys.argv params: $script $remote(repo) $url(remote repo url)
sys.argv params ctd: $local_ref $local_oid $remote_ref $remote_oid
Checks if we are performing a push update and not a push 
to delete a repo ... if conditions below both holds true:
local_oid(index 4) == '0000000000000000000000000000000000000000'
and if local_ref(index 3) == '(delete)' ...
"""
def confirm_non_delete_push():
    _, _, _, local_ref, local_oid, _, _ = sys.argv
    condition_1 = local_ref == CONSTANTS["DELETE_PUSH_REF_VALUE"]
    condition_2 = local_oid == CONSTANTS["DELETE_PUSH_HASH_VALUE"]
    return not(condition_1 and condition_2)

if __name__=="__main__":
    # only proceed if this is non-delete push
    if confirm_non_delete_push():
        # save the base directory path for namespaces included in
        # relevant files in dirs: i.e. Controllers and Attributes
        save_extensions_base_directory_path()

        # get the relevant paths and directories to init query
        swagger_filepath = get_swagger_file_path()
        root_dirs = get_root_directories()
        files_to_be_pushed = get_files_to_be_pushed()
        swagger_most_recent_mod = get_swagger_modified_datetime(swagger_filepath)
        global_most_recent_push = get_most_recent_push_datetime()
        
        # print("swagger_path: " + swagger_filepath)
        # print("root_dirs: ", root_dirs)
        # print("files_to_be_pushed: ", files_to_be_pushed)
        # print("swagger_mod_dt: ", swagger_most_recent_mod)
        # print("most_recent_push: ", global_most_recent_push)

        # only proceed if root_dirs != None
        if root_dirs:
            rebuild = check_for_api_committed_changes(root_dirs, 
                                                    swagger_most_recent_mod, 
                                                    global_most_recent_push,
                                                    files_to_be_pushed)
            handle_push(rebuild) # handles rebuilding before push
    
    # always return 0 for success
    sys.exit(0)