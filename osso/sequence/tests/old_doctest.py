# vim: set ts=8 sw=4 sts=4 et ai:
'''
>>> from osso.sequence import sequence
>>> sequence.create('1337')
Traceback (most recent call last):
    ...
SequenceError: invalid sequence name '1337'
>>> sequence.create('counter')  # default sequence
>>> sequence.create('invoice', start=100, increment=10)  # custom sequence
>>> sequence.create('invoice')  # create a sequence that already exists
Traceback (most recent call last):
    ...
SequenceError: sequence 'invoice' already exists
>>> sequence.currval('invoice')  # sequence has no value yet
Traceback (most recent call last):
    ...
SequenceError: sequence 'invoice' has no value
>>> int(sequence.nextval('invoice'))  # cast to avoid 100L vs 100
100
>>> int(sequence.nextval('counter'))
1
>>> int(sequence.nextval('invoice'))
110
>>> int(sequence.nextval('counter'))
2
>>> int(sequence.currval('invoice'))
110
>>> int(sequence.currval('counter'))
2
>>> sequence.setval('invoice', 1)
>>> int(sequence.currval('invoice'))
1
>>> sequence.drop('invoice')  # drop a sequence
>>> sequence.drop('invoice')  # drop a sequence that does not exist
Traceback (most recent call last):
    ...
SequenceDoesNotExist: sequence 'invoice' does not exist
>>> sequence.currval('invoice')  # currval of a sequence that does not exist
Traceback (most recent call last):
    ...
SequenceDoesNotExist: sequence 'invoice' does not exist
>>> sequence.nextval('invoice')  # nextval of a sequence that does not exist
Traceback (most recent call last):
    ...
SequenceDoesNotExist: sequence 'invoice' does not exist
>>> sequence.setval('invoice', 1)  # setval of a sequence that does not exist
Traceback (most recent call last):
    ...
SequenceDoesNotExist: sequence 'invoice' does not exist
'''
