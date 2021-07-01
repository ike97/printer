CC := gcc
CCFLAGS := -Wall
CLASS := printer

All:
	$(CC) $(CCFLAGS) $(CLASS).c -o $@

$(CLASS): $(CLASS).c $(CLASS).h
	$(CC) $(CCFLAGS) $(CLASS).c -o $@