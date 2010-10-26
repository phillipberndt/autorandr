#!/usr/bin/awk

/^[^ ]+ disconnected / {
	OUTPUT[$1] = "--off";
}

/^[^ ]+ connected / {
	split($3, A, "+");
	OUTPUT[$1] = "--mode "A[1]" --pos "A[2]"x"A[3];
}

END {
	printf "xrandr ";
	for (O in OUTPUT) {
		printf "--output " O " " OUTPUT[O] " ";
	}
	printf "\n";
}
