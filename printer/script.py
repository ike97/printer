import sys, os, re, time
from datetime import datetime

"""
A global dictionary of constants
"""
CONSTANTS = {
    "ISO_FORMAT_REGEX": r'\d+-\d+-\d+\s+\d+:\d+:\d+', # e.g. '2019-12-20 6:56:00'
    "PY_DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S", # e.g. '2019-12-20 6:56:00'
    "DEPENDENCY_REGEX": r'EdgeZoneRP.*;',
    "EDGEZONERP": "EdgeZoneRP"
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
Function returns the most recent global commit date
on the branch this to be pushed up to ADO
Assumes: push is current branch -> ADO
return: date (python datetime object)
"""
def get_most_recent_commit_datetime():
    commit_date_stream = os.popen("git log -n 1 --date=iso --pretty=format:%cd")
    commit_date = commit_date_stream.read().strip()
    most_recent_global_commit_date = get_formatted_datetime(commit_date)
    return most_recent_global_commit_date

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

    # in the event where most_recent_push_date == "",
    # the reg check below will still catch it and ret None
    # use regular expression to extract the date
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
    modified_date = os.path.getmtime(swagger_file_path)
    datetime_struct = time.strptime(time.ctime(modified_date))
    most_recent_modification_datetime = datetime.fromtimestamp(time.mktime(datetime_struct))
    return most_recent_modification_datetime

"""
Loops through selected repositories
----- API related directories -----
to query if any changes occurred since
last push and then enforces a build before
pushing up to ADO
@param: root_dirs [list of primary paths]
"""
def check_for_api_committed_changes(root_dirs, 
    swagger_most_recent_mod, global_most_recent_push, global_most_recent_commit):
    # validate input first...
    if not root_dirs: # null or empty
        return False # means no changes committed
    
    # boolean to keep track of whether we should rebuild project
    rebuild = False

    # loop through relevant dirs and sub-dirs to check
    for root_dir in root_dirs:
        # check every sub-dir ...
        for entry in os.listdir(root_dir):
            entry_path = f'{root_dir}\{entry}' # could be a file/dir
            print(entry_path)
            # get at most 2 most_recent_commit_dates
            commit_dates_stream = os.popen(f'git log -n 2 --date=iso --pretty=format:%cd {entry_path}')
            commit_dates = commit_dates_stream.readlines()
            print(commit_dates)
            if len(commit_dates) == 0:
                continue

            # otherwise implement logic defined in function comments
            most_recent_commit_dt = get_formatted_datetime(commit_dates[0])
            if not most_recent_commit_dt:
                print(most_recent_commit_dt)
                if len(commit_dates) == 1:
                    continue
                else:
                    most_recent_commit_dt = get_formatted_datetime(commit_dates[1])
                    if not most_recent_commit_dt:
                        continue

            # Here: most_recent_commit_dt must be defined for rest of logic
            # if swagger_most_recent_mod and most_recent_commit_dt > swagger_most_recent_mod:
            #     # condition == True means commits exist that haven't been built into swagger
            #     # This is more so for API definition changes etc. and not implementation focussed
            #     rebuild = True
            #     break
            
            # condition == True means unpushed commits exist, rebuild project
            # This is more focussed on API implementation changes which require a rebuild
            # of the project ...
            # if global_most_recent_push and most_recent_commit_dt > global_most_recent_push:
            #     rebuild = True
            #     break
            # elif global_most_recent_commit and most_recent_commit_dt == global_most_recent_commit:
                # incase this is our first build or first time pushing up the branch ... means we need to rebuild
                cond_1 = swagger_most_recent_mod == None
                cond_2 = global_most_recent_push == None
                cond_3 = len(commit_dates) == 1
                if cond_1 or cond_2 or cond_3: 
                    rebuild = True
                    break
                else:
                    # check to make sure that we got 2 unique commits from the git command
                    second_most_recent_commit_dt = get_formatted_datetime(commit_dates[1])
                    if len(commit_dates) == 2 and most_recent_commit_dt == second_most_recent_commit_dt:
                        rebuild = True
                        break
                    else:
                        # check to see if previous commit was built and if any changes made between prev commit
                        # and current commit ...
                        diff_exists = diff_most_recent_commits(entry_path) # check if diff exists between 1st and 2nd most recent 
                        cond_1 = swagger_most_recent_mod and second_most_recent_commit_dt > swagger_most_recent_mod
                        cond_2 = global_most_recent_push and second_most_recent_commit_dt > global_most_recent_push
                        if cond_1 or cond_2 or diff_exists: 
                            rebuild = True
                            break
            
            # check if entry_path == file_path then explore file_content 
            print("here: " + entry_path)
            if os.path.isdir(entry_path): # then it's a dir
                return check_for_api_committed_changes([entry_path], 
                                                        swagger_most_recent_mod, 
                                                        global_most_recent_push, 
                                                        global_most_recent_commit)
            else: # its a file hence explore the dependencies
                return explore_dependencies(entry_path,
                                            swagger_most_recent_mod, 
                                            global_most_recent_push, 
                                            global_most_recent_commit)

        # if rebuild flag set then exit
        if rebuild:
            break
    
    # return the rebuild flag/boolean
    return rebuild

"""
Function invokes the git diff file to check
to see if any modifications were made between 
files first and second commit of file @filepath
a boolean in effect...
param: file_path (str)
return: boolean (True if first_file != second_file)
"""
def diff_most_recent_commits(file_path):
    # get at most 2 most_recent_commit_dates
    commit_hashes_stream = os.popen(f'git log -n 2 --pretty=format:%H {file_path}')
    commit_hashes = commit_hashes_stream.readlines()
    if len(commit_hashes) < 2:
        return True
    else:
        commits_diff_stream = os.popen(f'git diff {commit_hashes[0]} {commit_hashes[1]}')
        commits_diff = commits_diff_stream.readlines()
        if commits_diff: # non-null and non-empty
            return True
        else:
            return False

"""
Function reads the content of the file for the
include lines: using .* and then parses it for
the section indicating the dependencies ...
param: file_path
default_path: C:/Users/t-isaacos/Desktop/Test/GitHooks/printer/headers.cs
"""
def explore_dependencies(file_path,
    swagger_most_recent_mod, global_most_recent_push, global_most_recent_commit):
    print("here")

    # reassign here but comment out ...
    file_path = "C:\\Users\\t-isaacos\\Desktop\\Test\\GitHooks\\printer\\headers.cs"

    if "win" in sys.platform:
        search_str = f'type {file_path} | findstr using'
    else:
        search_str = f'cat {file_path} | grep using'
    file_content_stream = os.popen(search_str)
    searched_file_content_arr = file_content_stream.readlines()
    if len(searched_file_content_arr) == 0:
        return False # means no rebuild necessary

    # otherwise extract the dependencies from the file...
    filtered_list = filter(lambda entry: CONSTANTS["EDGEZONERP"] in entry, searched_file_content_arr)
    # get the extension after "EdgeZoneRP" and build new paths for them...
    directories, files = get_full_path_for_extensions(None, filtered_list)
    # loop through the list and for each entry call appropraite function
    for file_path in files:
        print(file_path)
        if diff_most_recent_commits(file_path):
            return True

    # call the check_for_api function for the directories ...
    return check_for_api_committed_changes( directories,
                                            swagger_most_recent_mod,
                                            global_most_recent_push,
                                            global_most_recent_commit )
                                    
"""
Takes in list: e.g. "using .*.EdgeZoneRP.*;"
Filters this list and constructs a full path
to the dependency directories to perform full
search ... 
param: base_directory (str)
param: filtered_list (arr)
return: (result_dirs, result_files)
"""
def get_full_path_for_extensions(base_path, filtered_list):
    curr_dir = os.getcwd() if not base_path else base_path # base directory path
    result_dirs, result_files = [], []
    for entry in filtered_list:
        res = re.findall(CONSTANTS["DEPENDENCY_REGEX"], entry)
        if len(res) == 0:
            continue
        trimmed = res[0][len(CONSTANTS["EDGEZONERP"]):-1] # with sep='.'
        trimmed_mod_sep = trimmed.replace('.', "\\")
        # build the full path ... and add to list ...
        full_path = curr_dir + trimmed_mod_sep
        if os.path.isdir(full_path):
            result_dirs.append(full_path)
        else:
            result_files.append(full_path)
    # return the final list ...
    return result_dirs, result_files

"""
Function initiates rebuild by running
command: dotnet build build.proj
"""
def handle_push(rebuild):
    if rebuild:
        print("initiate rebuild")
    else:
        print("rebuild not necessary")
    

if __name__ == "__main__":
    # current_directory = os.getcwd()
    # check_for_api_committed_changes(current_directory)
    swagger_filepath = "C:/Users/t-isaacos/Desktop/Test/GitHooks/printer/script.sh"

    # get the necessary datetimes for validation
    swagger_most_recent_mod = get_swagger_modified_datetime(swagger_filepath)
    global_most_recent_push = get_most_recent_push_datetime()
    global_most_recent_commit = get_most_recent_commit_datetime()

    rebuild = check_for_api_committed_changes([os.getcwd()+"\\new"], 
                                                swagger_most_recent_mod, 
                                                global_most_recent_push,
                                                global_most_recent_commit)
    handle_push(rebuild) # handles pushing up repo