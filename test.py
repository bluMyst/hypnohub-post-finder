import http_server

if __name__ == '__main__':
    handler = http_server.RecommendationRequestHandler(('127.0.0.1', 8000))
    handler.server.serve_forever()
    #webbrowser.open('http://127.0.0.1:8000/')
