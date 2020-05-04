#include <signal.h>
#include <xcb/xcb.h>
#include <xcb/randr.h>
#include <getopt.h>
#include <unistd.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>

// indent -kr -i8
static int VERBOSE = 0;
extern char **environ;

static void sigterm_handler(int signum)
{
	signal(signum, SIG_DFL);
	kill(getpid(), signum);
}

static void ar_log(const char *format, ...)
{
	va_list args;

	if (!VERBOSE)
		return;
	va_start(args, format);
	vprintf(format, args);
	va_end(args);
	fflush(stdout);
}

static int ar_launch()
{
	pid_t pid = fork();
	if (pid == 0) {
		static char *argv[] =
		    { "/usr/bin/autorandr", "--change", "--default", "default", NULL };
		execve(argv[0], argv, environ);
		exit(127);
	} else {
		waitpid(pid, 0, 0);
	}
	return 0;
}

int main(int argc, char **argv)
{
	int help = 0;
	int version = 0;
	int daemonize = 0;

	const struct option long_options[] = {
		{ "help", no_argument, &help, 1 },
		{ "daemonize", no_argument, &daemonize, 1 },
		{ "version", no_argument, &version, 1 },
		{ "verbose", no_argument, &VERBOSE, 1 },
	};
	static const char *short_options = "hd";

	const char *help_str =
	    "Usage: autorandr_launcher [OPTION]\n"
	    "\n"
	    "Listens to X server screen change events and launches autorandr after an event occurs.\n"
	    "\n"
	    "\t-h,--help\t\t\tDisplay this help and exit\n"
	    "\t-d, --daemonize\t\t\tDaemonize program\n"
	    "\t--verbose\t\t\tOutput debugging information (prevents daemonizing)\n"
	    "\t--version\t\t\tDisplay version and exit\n";
	const char *version_str = "v.5\n";

	int option_index = 0;
	int ch = 0;
	while (ch != -1) {
		ch = getopt_long(argc, argv, short_options, long_options,
				 &option_index);
		switch (ch) {
		case 'h':
			help = 1;
			break;
		case 'd':
			daemonize = 1;
			break;
		}

	}

	if (help == 1) {
		printf("%s", help_str);
		exit(0);
	}
	if (version == 1) {
		printf("%s", version_str);
		exit(0);
	}
	// Check for already running daemon?

	// Daemonize
	if (daemonize == 1 && VERBOSE != 1) {
		struct sigaction sa;
		sa.sa_handler = sigterm_handler;
		sigemptyset(&sa.sa_mask);
		sa.sa_flags = 0;
		sigaction(SIGINT, &sa, NULL);
		sigaction(SIGTERM, &sa, NULL);
		sigaction(SIGQUIT, &sa, NULL);
		signal(SIGHUP, SIG_IGN);
		daemon(0, 0);
	}

	int screenNum;
	xcb_connection_t *c = xcb_connect(NULL, &screenNum);
	int conn_error = xcb_connection_has_error(c);
	if (conn_error) {
		fprintf(stderr, "Connection error!\n");
		exit(conn_error);
	}
	// Get the screen whose number is screenNum
	const xcb_setup_t *setup = xcb_get_setup(c);
	xcb_screen_iterator_t iter = xcb_setup_roots_iterator(setup);

	// we want the screen at index screenNum of the iterator
	for (int i = 0; i < screenNum; ++i) {
		xcb_screen_next(&iter);
	}
	xcb_screen_t *default_screen = iter.data;
	ar_log("Connected to server\n");

	// Subscribe to screen change events
	xcb_randr_select_input(c, default_screen->root,
			       XCB_RANDR_NOTIFY_MASK_SCREEN_CHANGE);
	xcb_flush(c);

	xcb_timestamp_t last_timestamp = (xcb_timestamp_t) 0;
	time_t last_time = time(NULL);
	while (1) {

		ar_log("Waiting for event\n");
		xcb_generic_event_t *evt = xcb_wait_for_event(c);
		if (!evt) {
			break;
		}

		// ar_log("Event type: %" PRIu8 "\n", evt->response_type);
		// ar_log("screen change masked: %" PRIu8 "\n",
		//       evt->response_type &
		//       XCB_RANDR_NOTIFY_MASK_SCREEN_CHANGE);

		if (evt->response_type &
		    XCB_RANDR_NOTIFY_MASK_SCREEN_CHANGE) {
			xcb_randr_screen_change_notify_event_t *randr_evt =
			    (xcb_randr_screen_change_notify_event_t *) evt;
			time_t evt_time = time(NULL);
			if ((randr_evt->timestamp > last_timestamp)
			    && (evt_time > last_time + 1)) {
				ar_log("Launch autorandr!\n");
				ar_launch();
				last_time = evt_time;
				last_timestamp = randr_evt->timestamp;
			}
		}

		free(evt);
	}

}
