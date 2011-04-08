# autorandr/auto-disper completion by Maciej 'macieks' Sitarz <macieks@freesco.pl>

_autorandr ()
{
	local cur prev opts lopts prfls

	COMPREPLY=()
	cur="${COMP_WORDS[COMP_CWORD]}"
	prev="${COMP_WORDS[COMP_CWORD-1]}"

	opts="-h -c -s -l -d"
	lopts="--help --change --save --load --default --force --fingerprint"
	prfls="`find ~/.autorandr/* -maxdepth 1 -type d -printf '%f\n'`"

	case "${cur}" in
		--*)
			COMPREPLY=( $( compgen -W "${lopts}" -- $cur ) )
			return 0
			;;
		-*)
			COMPREPLY=( $( compgen -W "${opts} ${lopts}" -- $cur ) )
			return 0
			;;
		*)
			if [ $COMP_CWORD -eq 1 ]; then
				COMPREPLY=( $( compgen -W "${opts} ${lopts}" -- $cur ) )
			fi
			;;
		esac

	case "${prev}" in
		-l|--load|-d|--default)
			COMPREPLY=( $( compgen -W "${prfls}" ) )
			return 0
			;;
		*)
			;;
	esac

	return 0
}
complete -F _autorandr autorandr
complete -F _autorandr auto-disper

