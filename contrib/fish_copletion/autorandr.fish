# don't complete directories and paths
complete -c autorandr -f

set -l virtual_profiles off common clone-largest horizontal vertical
set -l user_profiles (autorandr --list)
set -l profile_users -d --default -s --save -l --load -r --remove

complete -c autorandr -n "__fish_seen_subcommand_from $profile_users" \
    -a "$virtual_profiles $user_profiles"

complete -c autorandr -s -h -l help -d 'get help'
complete -c autorandr -s -c -l change -d 'automatically load the first detected profile'
complete -c autorandr -s -d -l default -d 'set default PROFILE'
complete -c autorandr -s -l -l load -d 'load PROFILE'
complete -c autorandr -s -s -l save -d 'save current setup to a PROFILE'
complete -c autorandr -s -r -l remove -d 'remove PROFILE'
complete -c autorandr -l current -d 'list curren active configurations'
complete -c autorandr -l cycle -d 'cycle through all detected drofiles'
complete -c autorandr -l config -d 'dump current xrandr setup'
complete -c autorandr -l debug -d 'enable verbose output'
complete -c autorandr -l dry-run -d 'don\'t change anything'
complete -c autorandr -l fingerprint -d 'fingerprint current hardware'
complete -c autorandr -l match-edid -d 'match displays using edid'
complete -c autorandr -l force -d 'force loading of a profile'
complete -c autorandr -l list -d 'list all profiles'
complete -c autorandr -l skip-options -d 'Set a comma-separated lis of xrandr arguments to skip buth in change detection and profile application'
complete -c autorandr -l ignore-lid -d 'By default, closed lids are considered as disconnected if other outputs are detected. This flag disables this behavior'
complete -c autorandr -l version -d 'show version'
