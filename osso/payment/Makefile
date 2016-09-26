# Makefile to quickly test non-django functionality

export PYTHONPATH=../..

.PHONY: all test
.SILENT:

all: test

test:
	@echo; for x in base.py xmlutils.py; do echo -n "Testing $$x: "; python $$x; echo; done
	@make -C provider
