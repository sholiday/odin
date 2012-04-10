test: all odin-test
all: odin_pb2.py odin-machine

odin-test:
	/usr/local/bin/python -u odinTest.py

odin-machine:
	/usr/local/bin/python -u odin.py

odin_pb2.py : odin.proto
	/usr/local/bin/protoc --python_out=. odin.proto