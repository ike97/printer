#!bin/bash

# function recursively returns path of all files
# $1 directory or subdirectory
function get_files(){
    local curr_dir=$1 # save the param and make local
    local doc_items=$(ls $curr_dir) # list the files in dir
    # echo "$doc_items"
    local local_files=() # declare local files list
    while [ ! ${#doc_items[@]} -eq 0 ];
    do
        # get the first item...
        entry=$doc_items
        entry_path="$curr_dir/$entry"
        
        if [[ -f $entry_path ]];
        then
            local_files+=( $entry_path )
        else
            # read the files and create paths
            local new_paths=$(ls $entry_path)
            for path in $new_paths
            do
                doc_items+=( "$entry/$path" )
            done
        fi

        # update the doc_items array...
        doc_items=${doc_items:1:(${#doc_items[@]} - 1)}
    done

    # for item in $doc_items
    # do
    #     entry_path="$curr_dir/$item"
    #     if [[ -f $entry_path ]];
    #     then
    #         local_files+=$entry_path
    #     else
    #         result+=$(get_files $entry_path)
    #         local_files+=$result
    #     fi
    # done

    # return the list of files found
    echo $local_files
}


# checks the last 2 commits of all the files
# $2 -> global date of most-recent-commit
# $1 -> dirlist [list of relevant files]
function  new_api_updates_committed(){
    echo $1
    echo $2
    update_committed=0 # boolean value to check to see if update was made
    for file in $1
    do
        # get the last 2 commits
        result=$(git log -n 2 --pretty=format:%cd $file)
        # echo $result
    done
    
    # date_length=${#most_recent_global_commit_date}
    # echo $date_length
    # res=$(git log -n 2 --pretty=format:%cd)
    # echo $res
    # # format for extracting dates ... ${parameter:offset:length}
    # result1=${res:0:$date_length}
    # result2=${res:$date_length:($date_length+1)}
}

# get the list of all files
current_directory=$(pwd)
most_recent_global_commit_date=$(git log -n 1 --pretty=format:%cd)
dirlist=$(get_files $current_directory)
# echo $dirlist
new_api_updates_committed "$dirlist" "$most_recent_global_commit_date"
echo $res