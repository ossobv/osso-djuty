# Makefile to quickly test non-django functionality

.PHONY: all test
.SILENT:

all: test

test:
	@echo; for x in xmlutils.py; do echo -n "Testing $$x: "; python $$x; echo; done
	@make -C provider
