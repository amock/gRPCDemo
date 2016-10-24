#!/usr/bin/env python3

import sys
import grpc

import stack_calc_pb2 as pb

class CalcClient:

  def __init__(self, host, port):
    self._channel = grpc.insecure_channel(host + ':' + port)
    self._stub = pb.StackCalcStub(self._channel)
    self._interacting = False

  def create_calc(self, args):
    if len(args):
      stack_depth = int(args[0])
    else:
      stack_depth = 3
    resp = self._stub.CreateCalc(pb.CreateCalcRequest(stack_depth=stack_depth))
    print(resp)

  def destroy_calc(self, args):
    calc_id = args[0]
    resp = self._stub.DestroyCalc(pb.DestroyCalcRequest(calc_id=calc_id))
    print(resp)

  def list_calcs(self, args):
    if len(args):
      limit = int(args[0])
    else:
      limit = 10
    resp = self._stub.ListCalcs(pb.ListCalcsRequest(limit=limit))
    print(resp)

  def eval_statement(self, args):
    calc_id = args[0]
    tokens, success = parse_tokens(args[1:])
    if not success:
      return
    req = pb.EvaluateStatementRequest(calc_id=calc_id, statement=pb.Statement(tokens=tokens))
    resp = self._stub.EvaluateStatement(req)
    print(resp)

  def get_state(self, args):
    if len(args) != 1:
      print('get expects on argument')
      return
    calc_id = args[0]
    resp = self._stub.GetState(pb.GetStateRequest(calc_id=calc_id))
    print(resp)

  def interact(self, args):
    try:
      self._interacting = True
      calc_id = args[0]
      print('grpcdemo [{}]> '.format(calc_id), end='', flush=True)
      responses = self._stub.Interact(self._interact_requests(calc_id))
      for response in responses:
        print(response)
        print('grpcdemo [{}]> '.format(calc_id), end='', flush=True)
    finally:
      self._interacting = False

  def _interact_requests(self, calc_id):
    while self._interacting:
      line = sys.stdin.readline()
      if not line:
        break
      parts = line.strip().split()
      if parts[0].lower() == 'stop':
        return
      ops, success = parse_tokens(parts)
      if not success:
        return
      req = pb.EvaluateStatementRequest(calc_id=calc_id, statement=pb.Statement(tokens=ops))
      yield req

def parse_tokens(tokens):
  ops = []
  for token in tokens:
    if token == '+':
      ops.append(pb.Statement.Token(op=pb.Statement.Token.ADD))
    elif token == '-':
      ops.append(pb.Statement.Token(op=pb.Statement.Token.SUBTRACT))
    elif token == '*':
      ops.append(pb.Statement.Token(op=pb.Statement.Token.MULTIPLY))
    elif token == '/':
      ops.append(pb.Statement.Token(op=pb.Statement.Token.DIVIDE))
    elif token == '.':
      ops.append(pb.Statement.Token(op=pb.Statement.Token.DROP))
    else:
      try:
        val = int(token)
        ops.append(pb.Statement.Token(op=pb.Statement.Token.VAL, val=val))
      except ValueError as e:
        print('Error parsing argument \'{}\': {}'.format(token, e))
        return [], False
  return ops, True

def main():
  client = CalcClient('localhost', '10000')
  commands = {
    'create': lambda x: client.create_calc(x),
    'destroy': lambda x: client.destroy_calc(x),
    'list': lambda x: client.list_calcs(x),
    'eval': lambda x: client.eval_statement(x),
    'get': lambda x: client.get_state(x),
    'interact': lambda x: client.interact(x)
  }

  print('grpcdemo> ', end='', flush=True)
  while True:
    line = sys.stdin.readline()
    if not line:
      break
    parts = line.strip().split()
    if not parts:
      print('Please enter a command.')
      continue
    command = parts[0]
    args = parts[1:]
    if command in commands:
      try:
        commands[command](args)
      except grpc.RpcError as e:
        print('Rpc failed with code: {}'.format(e.code()))
    else:
      print('Command not found: {}'.format(command))
    print('grpcdemo> ', end='', flush=True)
  print('Finished')

if __name__ == '__main__':
  main()
