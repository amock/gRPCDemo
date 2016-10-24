all: demo_client demo_server stackcalc/python/stack_calc_pb2.py

stackcalc/proto/stack_calc.pb.go: proto/stack_calc.proto
	mkdir -p stackcalc
	protoc --go_out=plugins=grpc:stackcalc proto/stack_calc.proto

stackcalc/python/stack_calc_pb2.py: proto/stack_calc.proto
	python -m grpc.tools.protoc -I=proto/ --python_out=python --grpc_python_out=python proto/stack_calc.proto

demo_client: stackcalc/proto/stack_calc.pb.go client/client.go
	go build -o demo_client ./client

demo_server: stackcalc/proto/stack_calc.pb.go server/server.go
	go build -o demo_server ./server

clean:
	rm -f demo_server demo_client stackcalc/proto/stack_calc.pb.go stackcalc/python/stack_calc_pb2.py
