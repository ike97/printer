#!bin/sh

most_recent_global_commit_date=$(git log -n 1 --pretty=format:%cd)
date_length=${#most_recent_global_commit_date}
echo $date_length
res=$(git log -n 2 --pretty=format:%cd)
echo $res
# format for extracting dates ... ${parameter:offset:length}
result1=${res:0:$date_length}
result2=${res:$date_length:($date_length+1)}

# compare the two dates for equality
[[ "$most_recent_global_commit_date" == "$result2" ]] && res="True" || res="False"
echo $res

echo $most_recent_global_commit_date == $result2

echo $result1 == $result2

# for commit in $res
# do
#     echo $commit
# done
echo $result1
echo $result2

# result=( ItemA ItemB )
# read -ra ADDR <<< "$result"
# echo $most_recent_global_commit_date
# echo $result
# for i in ${!result[@]}
# do
#     echo "$i" "${result[$i]}"
# done

# result=$(git diff ${result[@]})

# for i in ${!result[@]}
# do
#     echo "$i" "${result[$i]}" "\n"
# done

# if [[ -z result ]];
#     echo "Nope"
# fi

