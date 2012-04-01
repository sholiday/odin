test: all odin-test
all: proto

odin-test:
	/usr/local/bin/python -u odinTest.py

odin-machine:
	/usr/local/bin/python -u odin.py

proto:
	/usr/local/bin/protoc --python_out=. odin.proto