"""
Implémentation de la synchronisation par sémaphores.

Gère:
- La capacité des bus (nombre maximum de passagers)
- Le nombre maximum de bus aux arrêts

Utilise des sémaphores pour garantir:
- Qu'un bus ne dépasse jamais sa capacité
- Qu'un arrêt ne dépasse pas sa limite de bus
"""
import threading


class SemaphoreSyncManager:
    def __init__(self, bus_capacity: int, stop_limit: int):
        self.bus_capacity = bus_capacity
        self.stop_limit = stop_limit
        self.bus_sem = threading.Semaphore(bus_capacity)
        self.stop_sem = threading.Semaphore(stop_limit)
        self.bus_count = 0

