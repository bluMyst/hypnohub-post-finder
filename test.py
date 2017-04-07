import requests
import bs4
import pickle

import hypnohub_communication as hhcom
import http_server

if __name__ == '__main__':
    handler = http_server.RecommendationRequestHandler()
    handler.server.serve_forever()
