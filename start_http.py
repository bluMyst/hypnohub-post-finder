import http_server

server_address = ('127.0.0.1', 8000)
print("Serving on:",
      f"http://{server_address[0]}:{server_address[1]}/")
try:
    handler = http_server.RecommendationRequestHandler(server_address)
    handler.server.serve_forever()
except KeyboardInterrupt:
    pass
else:
    exit(1) # Just in case .serve_forever() fails somehow.
