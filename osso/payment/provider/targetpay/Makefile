export PYTHONPATH=../../../..

.PHONY: all test

all: test

test:
	@echo; for x in targetpay.py; do echo -n "Testing $$x: "; python $$x; echo; done
