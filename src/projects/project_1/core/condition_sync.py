"""
Implémentation de la synchronisation par variables de condition.

Gère:
- Coordination entre bus et passagers
- Synchronisation des départs de bus
- Gestion des correspondances

Utilise des variables de condition pour:
- Signaler les arrivées/départs des bus
- Coordonner les montées/descentes des passagers
- Gérer les attentes de correspondance
"""

import threading

class ConditionSyncManager:
    def __init__(self):
        self.bus_arrived = threading.Condition()
        self.bus_departed = threading.Condition()
        self.bus_waiting = threading.Condition()
        self.bus_waiting_count = 0
        self.bus_departed_count = 0
        self.bus_arrived_count = 0
