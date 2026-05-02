import time
from engine import SentinelRAGEngine

engine = SentinelRAGEngine()

queries = [
    "BNC",
    "Banco Nacional Cuba",
    "Random Fake Company",
    "La Compania General de Niquel"
] * 25

start = time.time()

for q in queries:
    engine.screen(q)

total_time = time.time() - start

print("Total queries:", len(queries))
print("Total time:", total_time)
print("Average latency:", total_time / len(queries))