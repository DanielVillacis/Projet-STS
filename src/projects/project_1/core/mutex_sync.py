"""
Implémentation de la synchronisation par mutex pour la gestion des accès concurrents.
"""
import threading 

class MutexSyncManager:
    def __init__(self):
        self.mutex = threading.Lock()
        self.balance = 0.0

    def acquire(self):
        self.mutex.acquire()

    def release(self):
        self.mutex.release()

    def paiement_trajet(self):
        self.acquire()
        try:
            if self.balance >= 3.5:
                self.balance -= 3.5
                print(f"Trajet payé: -3.50$, Solde actuel: {self.balance}$")
            else:
                print(f"Solde insuffisant: {self.balance}$")
        finally:
            self.release()

    def recharge(self, montant):
        self.acquire()
        try:
            self.balance += montant
            print(f"Recharge de {montant}$ effectuée, Solde actuel: {self.balance}$")
        finally:
            self.release()

    def remboursement(self, montant):
        self.acquire()
        try:
            self.balance += montant
            print(f"Remboursement de {montant}$ effectué, Solde actuel: {self.balance}$")
        finally:
            self.release()

    def achat_passe_mensuel(self):
        self.acquire()
        try:
            if self.balance >= 45.0:
                self.balance -= 45.0
                print(f"Passe mensuel acheté: -45.00$, Solde actuel: {self.balance}$")
            else:
                print(f"Solde insuffisant pour acheter la passe mensuel: {self.balance}$")
        finally:
            self.release()

class BusStop:
    def __init__(self, capacity):
        self.mutex = threading.Lock()
        self.capacity = capacity
        self.passengers = []

    def board_passenger(self, passenger):
        self.mutex.acquire()
        try:
            if len(self.passengers) < self.capacity:
                self.passengers.append(passenger)
                print(f"Passager {passenger} embarqué. Passagers actuels: {len(self.passengers)}")
            else:
                print(f"Capacité maximale atteinte. {passenger} refusé")
        finally:
            self.mutex.release()

    def unboard_passenger(self, passenger):
        self.mutex.acquire()
        try:
            if passenger in self.passengers:
                self.passengers.remove(passenger)
                print(f"Passager {passenger} descendu. Passagers actuels: {len(self.passengers)}")
            else:
                print(f"Passager {passenger} non trouvé dans le bus.")
        finally:
            self.mutex.release()
