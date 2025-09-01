import matlab.engine

print("Starting matlab")

eng = matlab.engine.start_matlab()

print("Calculate square root")
output = eng.sqrt(8.0)

print("Result:")
print (output)