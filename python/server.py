from concurrent import futures
import time

import grpc

import stack_calc_pb2 as pb

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

class Calc:

  def __init__(self, stack_depth):
    self._stack = []
    self._stack_depth = stack_depth

  @property
  def stack_depth(self):
    return self._stack_depth

  @property
  def stack(self):
    return self._stack

  def _get_vals(self):
    if len(self._stack) < 2:
      return pb.STACK_UNDERFLOW, None, None
    a = self._stack.pop()
    b = self._stack.pop()
    return pb.NO_ERROR, a, b

  def push_val(self, val):
    if len(self._stack) >= self._stack_depth:
      return pb.STACK_OVERFLOW
    self._stack.append(val)
    return pb.NO_ERROR

  def add(self):
    ret, a, b = self._get_vals()
    if ret != pb.NO_ERROR:
      return ret
    self._stack.append(a + b)
    return pb.NO_ERROR

  def subtract(self):
    ret, a, b = self._get_vals()
    if ret != pb.NO_ERROR:
      return ret
    self._stack.append(b - a)
    return pb.NO_ERROR

  def multiply(self):
    ret, a, b = self._get_vals()
    if ret != pb.NO_ERROR:
      return ret
    self._stack.append(a * b)
    return pb.NO_ERROR

  def divide(self):
    ret, a, b = self._get_vals()
    if ret != pb.NO_ERROR:
      return ret
    if a == 0:
      self._stack.append(b)
      self._stack.append(a)
      return pb.STACK_UNDERFLOW
    self._stack.append(b // a)
    return pb.NO_ERROR

  def drop(self):
    if len(self._stack) < 1:
      return pb.STACK_UNDERFLOW
    self._stack.pop()
    return pb.NO_ERROR

  def execute_token(self, token):
    op = token.op
    if op == pb.Statement.Token.VAL:
      return self.push_val(token.val)
    elif op == pb.Statement.Token.ADD:
      return self.add()
    elif op == pb.Statement.Token.SUBTRACT:
      return self.subtract()
    elif op == pb.Statement.Token.MULTIPLY:
      return self.multiply()
    elif op == pb.Statement.Token.DIVIDE:
      return self.divide()
    elif op == pb.Statement.Token.DROP:
      return self.drop()

class StackCalcServicer(pb.StackCalcServicer):

  def __init__(self):
    self._calcs = {}
    self._next_calc = 0

  def CreateCalc(self, request, context):
    """Create a Calc instance and return its ID
    """
    print('Received CreateCalc {}'.format(request))
    calc_id = hex(self._next_calc)[2:]
    self._calcs[calc_id] = Calc(request.stack_depth)
    self._next_calc += 1
    return pb.CreateCalcResponse(calc_id=calc_id)

  def DestroyCalc(self, request, context):
    """Destroy the specified Calc instance
    """
    print('Received DestroyCalc {}'.format(request))
    del self._calcs[request.calc_id]
    return pb.DestroyCalcResponse()

  def ListCalcs(self, request, context):
    """Lists existing Calc instances
    """
    print('Received ListCalcs {}'.format(request))
    return pb.ListCalcsResponse(calc_ids=list(self._calcs.keys()))

  def _eval(self, request):
    calc = self._calcs[request.calc_id]
    for token in request.statement.tokens:
        err = calc.execute_token(token)
        if err != pb.NO_ERROR:
          return pb.EvaluateStatementResponse()
    state = pb.State(stack_depth=calc.stack_depth, vals=calc.stack)
    resp = pb.EvaluateStatementResponse(state=state, err=err)
    return resp

  def EvaluateStatement(self, request, context):
    """Evaluates the specified statement and returns the state of the Calc after the
    evaluation.  If an error occurs then that is returned as well
    """
    print('Received EvaluateStatement {}'.format(request))
    try:
      return self._eval(request)
    except KeyError:
      context.set_code(grpc.StatusCode.NOT_FOUND)
      context.set_details('Calc not found for ID \'{}\''.format(request.calc_id))
      return pb.EvaluateStatementResponse()

  def GetState(self, request, context):
    """Returns the state of the specified Calc
    """
    print('Received GetState {}'.format(request))
    try:
      calc = self._calcs[request.calc_id]
    except KeyError:
      context.set_code(grpc.StatusCode.NOT_FOUND)
      context.set_details('Calc not found for ID \'{}\''.format(request.calc_id))
      return pb.GetStateResponse()
    state = pb.State(stack_depth=calc.stack_depth, vals=calc.stack)
    return pb.GetStateResponse(state=state)

  def Interact(self, request_iterator, context):
    print('Starting bidirectional streaming')
    for req in request_iterator:
      print('Received request on stream {}'.format(req))
      try:
        resp = self._eval(req)
        print('Sending response on stream {}'.format(resp))
        yield resp
      except KeyError:
        print('Error during streaming')
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details('Calc not found for ID \'{}\''.format(req.calc_id))
        return


def serve():
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
  pb.add_StackCalcServicer_to_server(StackCalcServicer(), server)
  server.add_insecure_port('[::]:10000')
  server.start()
  try:
    while True:
      time.sleep(_ONE_DAY_IN_SECONDS)
  except KeyboardInterrupt:
    server.stop(0)

if __name__ == '__main__':
  serve()
