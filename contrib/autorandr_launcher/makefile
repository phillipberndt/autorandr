CFLAGS  = -pipe \
	-o2 \
	-Wstrict-overflow=5 -fstack-protector-all \
	-W -Wall -Wextra \
	-Wbad-function-cast \
	-Wcast-align \
	-Wcast-qual \
	-Wconversion \
	-Wfloat-equal \
	-Wformat-y2k \
	-Winit-self \
	-Winline \
	-Winvalid-pch \
	-Wmissing-declarations \
	-Wmissing-field-initializers \
	-Wmissing-format-attribute \
	-Wmissing-include-dirs \
	-Wmissing-noreturn \
	-Wmissing-prototypes \
	-Wnested-externs \
	-Wnormalized=nfc \
	-Wold-style-definition \
	-Woverlength-strings \
	-Wpacked \
	-Wpadded \
	-Wpointer-arith \
	-Wredundant-decls \
	-Wshadow \
	-Wsign-compare \
	-Wstack-protector \
	-Wstrict-aliasing=2 \
	-Wstrict-prototypes \
	-Wundef \
	-Wunsafe-loop-optimizations \
	-Wvolatile-register-var \
	-Wwrite-strings


LAUNCHER_LDLIBS=$(shell pkg-config --libs pkg-config xcb xcb-randr 2>/dev/null)
LAUNCHER_CFLAGS=$(shell pkg-config --cflags pkg-config xcb xcb-randr 2>/dev/null)
USER_DEFS="-DAUTORANDR_PATH=\"$(shell which autorandr 2>/dev/null)\""
#------------------------------------------------------------------------------
.PHONY : all clean

#------------------------------------------------------------------------------
all : autorandr-launcher

autorandr-launcher: autorandr_launcher.c
	$(CC) $(CFLAGS) $(LAUNCHER_CFLAGS) $(USER_DEFS) -o $@ $+ $(LAUNCHER_LDLIBS)

#------------------------------------------------------------------------------
clean :
	$(RM) autorandr-launcher *.o
