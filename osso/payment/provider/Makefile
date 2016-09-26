.PHONY: all test
.SILENT:

all: test

test:
	@for provider in [a-z]*; do make -C $$provider; done
